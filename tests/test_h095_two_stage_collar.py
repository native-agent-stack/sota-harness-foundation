"""Unit & Hypothesis property tests for Trial #95 (`H095`) Two-Stage Lit-Queue -> Collar Execution."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cc_sota_harness.h095_two_stage_hybrid_collar_prewall import (
    H095_HYPOTHESIS_ID,
    H095_SPEC_SHA256,
    H095_TRIAL_N,
    is_lit_roundlot_queue_trade,
    simulate_h095_two_stage_hybrid_orb_fill,
)
from cc_sota_harness.passive_bid_trail_prewall import QuoteTickNs, TradePrintNs


def test_h095_constants_and_lit_roundlot_filter() -> None:
    assert H095_TRIAL_N == 95
    assert H095_HYPOTHESIS_ID == "H095_TWO_STAGE_LIT_QUEUE_15S_TO_10BPS_MARKETABLE_COLLAR_ORB_CPCV"
    assert len(H095_SPEC_SHA256) == 64

    assert is_lit_roundlot_queue_trade("Q", ["F"], 100.0) is True
    assert is_lit_roundlot_queue_trade("D", [], 500.0) is False
    assert is_lit_roundlot_queue_trade("N", ["I"], 200.0) is False
    assert is_lit_roundlot_queue_trade("P", [], 99.0) is False


def test_h095_stage1_passive_precedes_stage2_collar() -> None:
    ns0 = 1_000_000_000_000
    quotes = (
        QuoteTickNs(ts_ns=ns0 + 1_000_000_000, bid_px=50.00, bid_lots=1.0, ask_px=50.03, ask_lots=5.0),
        QuoteTickNs(ts_ns=ns0 + 14_000_000_000, bid_px=50.01, bid_lots=2.0, ask_px=50.04, ask_lots=5.0),
    )
    # 250 shares at 50.00 depletes 100 front shares + 100 order shares at +2s
    trades = (TradePrintNs(ts_ns=ns0 + 2_000_000_000, price_px=50.00, size_shares=250.0),)
    res = simulate_h095_two_stage_hybrid_orb_fill(
        ns_entry=ns0,
        bp_entry=50.00,
        bs_entry_lots=1.0,
        ap_entry=50.03,
        order_qty_shares=100.0,
        lit_roundlot_trades=trades,
        post_entry_quotes=quotes,
    )
    assert res.filled is True
    assert res.fill_stage.startswith("stage1_passive_")
    assert res.fill_px == pytest.approx(50.00)
    assert res.fill_ts_ns == ns0 + 2_000_000_000


@settings(max_examples=80, deadline=None)
@given(
    ap0=st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    drift_bps=st.floats(min_value=-5.0, max_value=25.0, allow_nan=False, allow_infinity=False),
    spread_bps=st.floats(min_value=1.0, max_value=18.0, allow_nan=False, allow_infinity=False),
    ask_lots=st.floats(min_value=0.5, max_value=20.0, allow_nan=False, allow_infinity=False),
)
def test_property_h095_stage2_collar_never_chases_beyond_10bps(
    ap0: float,
    drift_bps: float,
    spread_bps: float,
    ask_lots: float,
) -> None:
    ns0 = 2_000_000_000_000
    bp0 = ap0 * 0.9994
    ap15 = ap0 * (1.0 + drift_bps / 10_000.0)
    bp15 = ap15 * (1.0 - spread_bps / 10_000.0)
    quotes = (
        QuoteTickNs(ts_ns=ns0 + 14_500_000_000, bid_px=bp15, bid_lots=3.0, ask_px=ap15, ask_lots=ask_lots),
    )
    res = simulate_h095_two_stage_hybrid_orb_fill(
        ns_entry=ns0,
        bp_entry=bp0,
        bs_entry_lots=5.0,
        ap_entry=ap0,
        order_qty_shares=200.0,
        lit_roundlot_trades=(),
        post_entry_quotes=quotes,
    )
    if res.filled:
        assert res.fill_stage == "stage2_collar_15s"
        assert res.fill_px == pytest.approx(ap15)
        assert res.ask_drift_15s_bps <= 10.0001
        assert res.spread_15s_bps <= 10.0001
        assert ask_lots * 100.0 >= 200.0 - 1e-9
    else:
        assert res.fill_stage == "collar_rejected"
