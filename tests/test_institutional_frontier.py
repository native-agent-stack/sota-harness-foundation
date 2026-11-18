"""Tests for Wave-2 Institutional Frontier Modules (Impact, 23/5 SIP+BOATS, PIT Master, Stateful FSM Fuzzing)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Literal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from cc_sota_harness.institutional_frontier import (
    NEW_YORK,
    AuctionPrintCandidate,
    PaperPositionGuardianFSM,
    PITSecurityMaster,
    PITSecurityRecord,
    VenueQuote,
    almgren_chriss_sqrt_impact_bps,
    check_one_writer_symbol_isolation,
    is_cta_utp_iso_print,
    resolve_245_session_window,
    select_freshest_venue_quote,
    select_listing_exchange_auction_print,
)


def test_cta_utp_iso_code_f_vs_oddlot_i() -> None:
    assert is_cta_utp_iso_print(["@", "F"]) is True
    assert is_cta_utp_iso_print(["@", "I"]) is False  # 'I' is Odd Lot in CTA/UTP codes.json, NOT ISO!
    assert is_cta_utp_iso_print([]) is False


@given(
    q1=st.floats(min_value=10.0, max_value=5_000.0, allow_nan=False, allow_infinity=False),
    q_extra=st.floats(min_value=1.0, max_value=5_000.0, allow_nan=False, allow_infinity=False),
    vol_bucket=st.floats(min_value=10_000.0, max_value=2_000_000.0, allow_nan=False, allow_infinity=False),
    sigma_bps=st.floats(min_value=5.0, max_value=300.0, allow_nan=False, allow_infinity=False),
)
def test_property_sqrt_market_impact_monotonic_and_sublinear(
    q1: float,
    q_extra: float,
    vol_bucket: float,
    sigma_bps: float,
) -> None:
    imp1 = almgren_chriss_sqrt_impact_bps(
        order_shares=q1,
        bucket_volume_shares=vol_bucket,
        intraday_volatility_bps=sigma_bps,
    )
    imp2 = almgren_chriss_sqrt_impact_bps(
        order_shares=q1 + q_extra,
        bucket_volume_shares=vol_bucket,
        intraday_volatility_bps=sigma_bps,
    )
    imp_quad = almgren_chriss_sqrt_impact_bps(
        order_shares=4.0 * q1,
        bucket_volume_shares=vol_bucket,
        intraday_volatility_bps=sigma_bps,
    )
    assert imp2 > imp1 > 0.0
    assert imp_quad == pytest.approx(2.0 * imp1, rel=1e-9)


def test_dec6_235_sip_flag_holidays_halfdays_and_nanosecond_freshness() -> None:
    # 1. Thanksgiving noon -> HOLIDAY_CLOSED (not eligible!)
    tg_noon = dt.datetime(2026, 11, 26, 12, 0, tzinfo=NEW_YORK)
    w_tg = resolve_245_session_window(tg_noon, enable_dec6_235_sip=False)
    assert w_tg.session == "HOLIDAY_CLOSED" and not w_tg.is_entry_eligible

    # 2. Black Friday half-day: 12:30 ET -> REGULAR_RTH with 12:55 ET flatten; 17:01 ET -> EARLY_POSTMARKET_CLOSED
    bf_rth = resolve_245_session_window(dt.datetime(2026, 11, 27, 12, 30, tzinfo=NEW_YORK))
    assert bf_rth.session == "REGULAR_RTH"
    assert bf_rth.rth_flatten_time_et == dt.time(12, 55)

    bf_after = resolve_245_session_window(dt.datetime(2026, 11, 27, 17, 1, tzinfo=NEW_YORK))
    assert bf_after.session == "EARLY_POSTMARKET_CLOSED" and not bf_after.is_entry_eligible

    # 3. Sunday Dec 6, 2026 20:30 ET: BOATS stays eligible during NMS 20:00-21:00 pause!
    dec6_2030 = dt.datetime(2026, 12, 6, 20, 30, tzinfo=NEW_YORK)
    assert resolve_245_session_window(dec6_2030, enable_dec6_235_sip=True).session == "OVERNIGHT_BOATS"

    # 4. Sunday Dec 6, 2026 21:15 ET: flag False -> OVERNIGHT_BOATS; flag True -> OVERNIGHT_NMS_235_AND_BOATS
    dec6_2115 = dt.datetime(2026, 12, 6, 21, 15, tzinfo=NEW_YORK)
    assert resolve_245_session_window(dec6_2115, enable_dec6_235_sip=False).session == "OVERNIGHT_BOATS"
    assert resolve_245_session_window(dec6_2115, enable_dec6_235_sip=True).session == "OVERNIGHT_NMS_235_AND_BOATS"

    # 5. Sub-second nanosecond freshness & 04:00 ET stale BOATS expiration
    base_ns = 1_796_691_600_000_000_000
    boats = VenueQuote(venue="BOATS", price=99.0, event_ts_ns=base_ns + 100_000_000)
    sip_newer = VenueQuote(venue="SIP", price=101.0, event_ts_ns=base_ns + 400_000_000)
    chosen = select_freshest_venue_quote(
        session="OVERNIGHT_NMS_235_AND_BOATS",
        as_of_ns=base_ns + 500_000_000,
        sip_quote=sip_newer,
        boats_quote=boats,
    )
    assert chosen == sip_newer

    # At 04:00 ET PREMARKET, BOATS is ineligible and stale cached BOATS cannot beat fresh SIP
    pre_chosen = select_freshest_venue_quote(
        session="PREMARKET",
        as_of_ns=base_ns + 500_000_000,
        sip_quote=sip_newer,
        boats_quote=VenueQuote(venue="BOATS", price=99.0, event_ts_ns=base_ns + 490_000_000),
    )
    assert pre_chosen == sip_newer


def test_pit_security_master_prevents_ticker_reuse_contamination() -> None:
    master = PITSecurityMaster(
        [
            PITSecurityRecord(
                ticker="XYZ",
                cik="0001111111",
                composite_figi="BBG000OLD001",
                valid_from=dt.date(2024, 1, 1),
                valid_to=dt.date(2025, 6, 30),
                delisted_date=dt.date(2025, 6, 30),
            ),
            PITSecurityRecord(
                ticker="XYZ",
                cik="0002222222",
                composite_figi="BBG000NEW002",
                valid_from=dt.date(2025, 9, 1),
                valid_to=None,
            ),
        ]
    )
    old_rec = master.resolve("XYZ", dt.date(2025, 3, 15))
    gap_rec = master.resolve("XYZ", dt.date(2025, 8, 1))
    new_rec = master.resolve("XYZ", dt.date(2026, 10, 14))
    assert old_rec is not None and old_rec.cik == "0001111111"
    assert gap_rec is None
    assert new_rec is not None and new_rec.cik == "0002222222"


class GuardianLifecycleMachine(RuleBasedStateMachine):
    """Stateful Hypothesis fuzzer proving zero naked-position states across 24/5 transitions."""

    def __init__(self) -> None:
        super().__init__()
        self.fsm = PaperPositionGuardianFSM()

    @invariant()
    def always_protected_and_within_200_rpm(self) -> None:
        self.fsm.assert_invariants()

    @rule(
        shares=st.integers(min_value=1, max_value=500),
        stop_bps=st.integers(min_value=10, max_value=200),
    )
    def try_enter_long(self, shares: int, stop_bps: int) -> None:
        if self.fsm.open_shares != 0:
            return
        entry = Decimal("100.00")
        stop = entry * (Decimal("10000") - Decimal(stop_bps)) / Decimal("10000")
        try:
            self.fsm.enter_long(shares, entry, stop)
        except RuntimeError:
            pass  # Rate-budget refusal leaves flat position safe

    @rule(delta=st.integers(min_value=1, max_value=100))
    def try_partial_fill(self, delta: int) -> None:
        try:
            self.fsm.add_partial_fill(delta)
        except RuntimeError:
            pass

    @rule(target_session=st.sampled_from(["rth", "extended", "overnight"]))
    def try_session_transition(self, target_session: Literal["rth", "extended", "overnight"]) -> None:
        try:
            self.fsm.transition_session(target_session)
        except RuntimeError:
            pass

    @rule(ratchet_cents=st.integers(min_value=1, max_value=150))
    def try_ratchet(self, ratchet_cents: int) -> None:
        if self.fsm.open_shares <= 0:
            return
        candidate = self.fsm.stop_price + (Decimal(ratchet_cents) / Decimal("100"))
        try:
            self.fsm.ratchet_stop_up(candidate)
        except RuntimeError:
            pass

    @rule()
    def try_flatten(self) -> None:
        try:
            self.fsm.flatten()
        except RuntimeError:
            pass

    @rule()
    def try_reset_minute(self) -> None:
        self.fsm.reset_minute_window()


TestGuardianStatefulFuzz = GuardianLifecycleMachine.TestCase
TestGuardianStatefulFuzz.settings = settings(max_examples=80, stateful_step_count=35)


def test_harvested_auction_6_before_m_and_one_writer_isolation() -> None:
    arca_m = AuctionPrintCandidate(venue="P", price=24.12, size=50_000, condition="M", event_ts_ns=100)
    nasdaq_6 = AuctionPrintCandidate(venue="Q", price=24.50, size=8_000, condition="6", event_ts_ns=200)
    assert select_listing_exchange_auction_print(side="c", prints=[arca_m, nasdaq_6]) == nasdaq_6

    open_q = AuctionPrintCandidate(venue="Q", price=10.10, size=90_000, condition="Q", event_ts_ns=10)
    open_o_small = AuctionPrintCandidate(venue="N", price=10.05, size=2_000, condition="O", event_ts_ns=12)
    open_o_big = AuctionPrintCandidate(venue="Q", price=10.08, size=15_000, condition="O", event_ts_ns=15)
    assert select_listing_exchange_auction_print(side="o", prints=[open_q, open_o_small, open_o_big]) == open_o_big

    check_one_writer_symbol_isolation(
        symbol="NVDA",
        writer_lane_id="paper-lane-a",
        open_position_lanes={"NVDA": "paper-lane-a"},
        open_order_lanes={},
    )
    with pytest.raises(PermissionError, match="hard-refused"):
        check_one_writer_symbol_isolation(
            symbol="NVDA",
            writer_lane_id="paper-lane-a",
            open_position_lanes={},
            open_order_lanes={},
            is_blind_close_position=True,
        )
    with pytest.raises(PermissionError, match="hard-refused"):
        check_one_writer_symbol_isolation(
            symbol="NVDA",
            writer_lane_id="paper-lane-b",
            open_position_lanes={"NVDA": "paper-lane-a"},
            open_order_lanes={},
        )
