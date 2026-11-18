"""Institutional Frontier Modules (Wave 2): Impact, 23/5 SIP+BOATS Cutover, PIT Master & Guardian FSM.

Closes the four post-audit institutional capabilities identified by CC Lead, GPT-6.2 Astra,
and the 404-repo SOTA gap analysis:
1. Almgren-Chriss square-root intraday participation market-impact + borrow-decay model (`_bps`).
2. Flag-gated (`enable_dec6_235_sip=False` default) XNYS holiday/half-day/24x5 session & nanosecond
   SIP/BOATS quote-freshness resolver (fixing integer-second truncation, 04:00 ET stale BOATS carry,
   13:00 ET half-day flatten, and Dec-6 20:00-21:00 ET ATS eligibility).
3. Point-in-Time (`PIT`) survivorship-free `CIK <-> Composite FIGI <-> Ticker` interval resolver.
4. Deterministic `PaperPositionGuardianFSM` verified by Hypothesis `RuleBasedStateMachine` to
   guarantee zero naked shares across RTH/Extended/Overnight transitions and partial fills.
"""

from __future__ import annotations

import datetime as dt
import functools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

import exchange_calendars as xcals

from cc_sota_harness.gates import ALPACA_PAPER_MAX_RPM, MAX_PROTECTIVE_STOP_PCT, PROTECTIVE_EXIT_RESERVE_RPM

NEW_YORK = ZoneInfo("America/New_York")
DEC6_235_CUTOVER_DATE = dt.date(2026, 12, 6)
CTA_UTP_ISO_CONDITION_CODE = "F"


def is_cta_utp_iso_print(conditions: Sequence[str] | None) -> bool:
    """Return True iff consolidated CTA/UTP trade conditions contain 'F' (ISO, not 'I' Odd Lot)."""
    if not conditions:
        return False
    return CTA_UTP_ISO_CONDITION_CODE in conditions


SessionKind = Literal[
    "REGULAR_RTH",
    "PREMARKET",
    "POSTMARKET",
    "OVERNIGHT_BOATS",
    "OVERNIGHT_NMS_235_AND_BOATS",
    "HOLIDAY_CLOSED",
    "EARLY_POSTMARKET_CLOSED",
    "WEEKEND_CLOSED",
]


@functools.lru_cache(maxsize=1)
def _xnys_calendar() -> xcals.ExchangeCalendar:
    return xcals.get_calendar("XNYS")


def almgren_chriss_sqrt_impact_bps(
    *,
    order_shares: float,
    bucket_volume_shares: float,
    intraday_volatility_bps: float,
    impact_coeff_y: float = 0.65,
    borrow_fee_annual_bps: float = 0.0,
    holding_days: float = 0.0,
) -> float:
    """Compute one-way square-root participation impact + short-borrow carry in basis points."""
    for name, val in (
        ("order_shares", order_shares),
        ("bucket_volume_shares", bucket_volume_shares),
        ("intraday_volatility_bps", intraday_volatility_bps),
        ("impact_coeff_y", impact_coeff_y),
        ("borrow_fee_annual_bps", borrow_fee_annual_bps),
        ("holding_days", holding_days),
    ):
        if not math.isfinite(val):
            raise ValueError(f"{name} must be finite, got {val}")
    if order_shares < 0.0:
        raise ValueError(f"order_shares must be >= 0, got {order_shares}")
    if bucket_volume_shares <= 0.0:
        raise ValueError(f"bucket_volume_shares must be > 0, got {bucket_volume_shares}")
    if intraday_volatility_bps < 0.0 or impact_coeff_y < 0.0 or borrow_fee_annual_bps < 0.0 or holding_days < 0.0:
        raise ValueError("volatility, impact_coeff_y, borrow_fee_annual_bps, and holding_days must be >= 0")

    if order_shares == 0.0:
        return (borrow_fee_annual_bps / 252.0) * holding_days

    participation = order_shares / bucket_volume_shares
    market_impact_bps = impact_coeff_y * intraday_volatility_bps * math.sqrt(participation)
    borrow_carry_bps = (borrow_fee_annual_bps / 252.0) * holding_days
    return market_impact_bps + borrow_carry_bps


@dataclass(frozen=True, slots=True)
class SessionWindowInfo:
    session: SessionKind
    trade_date: dt.date
    is_entry_eligible: bool
    rth_flatten_time_et: dt.time | None


def resolve_245_session_window(
    ts: dt.datetime,
    *,
    enable_dec6_235_sip: bool = False,
) -> SessionWindowInfo:
    """Resolve exact XNYS + BOATS + optional Dec-6 23/5 SIP session eligibility."""
    if ts.tzinfo is None:
        raise ValueError("ts must be timezone-aware")
    ny = ts.astimezone(NEW_YORK)
    cal = _xnys_calendar()
    d = ny.date()
    minute_of_day = ny.hour * 60 + ny.minute

    # Evening 20:00..23:59:59.999999 ET belongs to the next calendar day's overnight session.
    if minute_of_day >= 20 * 60:
        next_day = d + dt.timedelta(days=1)
        if not cal.is_session(next_day.isoformat()):
            kind: SessionKind = "WEEKEND_CLOSED" if next_day.weekday() >= 5 else "HOLIDAY_CLOSED"
            return SessionWindowInfo(
                session=kind, trade_date=next_day, is_entry_eligible=False, rth_flatten_time_et=None
            )
        if enable_dec6_235_sip and d >= DEC6_235_CUTOVER_DATE and minute_of_day >= 21 * 60:
            return SessionWindowInfo(
                session="OVERNIGHT_NMS_235_AND_BOATS",
                trade_date=next_day,
                is_entry_eligible=True,
                rth_flatten_time_et=None,
            )
        # Between 20:00 and 21:00 ET (including post-Dec-6 NMS pause), BOATS ATS remains eligible!
        return SessionWindowInfo(
            session="OVERNIGHT_BOATS",
            trade_date=next_day,
            is_entry_eligible=True,
            rth_flatten_time_et=None,
        )

    # 00:00..03:59:59.999999 ET belongs to today's overnight session if today is an XNYS session.
    if minute_of_day < 4 * 60:
        if not cal.is_session(d.isoformat()):
            kind = "WEEKEND_CLOSED" if d.weekday() >= 5 else "HOLIDAY_CLOSED"
            return SessionWindowInfo(session=kind, trade_date=d, is_entry_eligible=False, rth_flatten_time_et=None)
        prev_evening = d - dt.timedelta(days=1)
        if enable_dec6_235_sip and prev_evening >= DEC6_235_CUTOVER_DATE:
            return SessionWindowInfo(
                session="OVERNIGHT_NMS_235_AND_BOATS",
                trade_date=d,
                is_entry_eligible=True,
                rth_flatten_time_et=None,
            )
        return SessionWindowInfo(
            session="OVERNIGHT_BOATS",
            trade_date=d,
            is_entry_eligible=True,
            rth_flatten_time_et=None,
        )

    # 04:00..19:59:59.999999 ET: today must be a valid XNYS session.
    if not cal.is_session(d.isoformat()):
        kind = "WEEKEND_CLOSED" if d.weekday() >= 5 else "HOLIDAY_CLOSED"
        return SessionWindowInfo(session=kind, trade_date=d, is_entry_eligible=False, rth_flatten_time_et=None)

    close_ny = cal.session_close(d.isoformat()).to_pydatetime().astimezone(NEW_YORK)
    close_minute = close_ny.hour * 60 + close_ny.minute  # 960 (16:00) normal, 780 (13:00) half-day
    postmarket_end_minute = close_minute + 240  # +4h: 20:00 normal, 17:00 on 13:00 early close
    flatten_dt = (close_ny - dt.timedelta(minutes=5)).timetz().replace(tzinfo=None)

    if minute_of_day < 9 * 60 + 30:
        return SessionWindowInfo(
            session="PREMARKET", trade_date=d, is_entry_eligible=True, rth_flatten_time_et=flatten_dt
        )
    if minute_of_day < close_minute:
        return SessionWindowInfo(
            session="REGULAR_RTH",
            trade_date=d,
            is_entry_eligible=True,
            rth_flatten_time_et=flatten_dt,
        )
    if minute_of_day < postmarket_end_minute:
        return SessionWindowInfo(
            session="POSTMARKET",
            trade_date=d,
            is_entry_eligible=True,
            rth_flatten_time_et=flatten_dt,
        )
    return SessionWindowInfo(
        session="EARLY_POSTMARKET_CLOSED",
        trade_date=d,
        is_entry_eligible=False,
        rth_flatten_time_et=flatten_dt,
    )


@dataclass(frozen=True, slots=True)
class VenueQuote:
    venue: Literal["SIP", "BOATS"]
    price: float
    event_ts_ns: int


def select_freshest_venue_quote(
    *,
    session: SessionKind,
    as_of_ns: int,
    sip_quote: VenueQuote | None,
    boats_quote: VenueQuote | None,
    max_staleness_ns: int = 300_000_000_000,  # 5 minutes default
) -> VenueQuote | None:
    """Select the freshest session-eligible quote using full nanosecond timestamps."""
    if max_staleness_ns <= 0:
        raise ValueError("max_staleness_ns must be > 0")

    eligible: list[VenueQuote] = []
    allow_sip = session in ("PREMARKET", "REGULAR_RTH", "POSTMARKET", "OVERNIGHT_NMS_235_AND_BOATS")
    allow_boats = session in ("OVERNIGHT_BOATS", "OVERNIGHT_NMS_235_AND_BOATS")

    for q, allowed in ((sip_quote, allow_sip), (boats_quote, allow_boats)):
        if q is None or not allowed:
            continue
        if not math.isfinite(q.price) or q.price <= 0.0:
            raise ValueError(f"Invalid quote price on {q.venue}: {q.price}")
        if q.event_ts_ns > as_of_ns:
            continue  # Never peek into post-as-of future prints
        if (as_of_ns - q.event_ts_ns) > max_staleness_ns:
            continue  # Expire prior-session / stale cached snapshots
        eligible.append(q)

    if not eligible:
        return None
    # Sort by (event_ts_ns DESC, SIP preferred on exact nanosecond tie)
    eligible.sort(key=lambda item: (item.event_ts_ns, 1 if item.venue == "SIP" else 0), reverse=True)
    return eligible[0]


@dataclass(frozen=True, slots=True)
class PITSecurityRecord:
    ticker: str
    cik: str
    composite_figi: str
    valid_from: dt.date
    valid_to: dt.date | None
    delisted_date: dt.date | None = None


class PITSecurityMaster:
    """Point-in-Time survivorship-free symbol resolver preventing ticker-reuse join contamination."""

    def __init__(self, records: list[PITSecurityRecord]) -> None:
        by_ticker: dict[str, list[PITSecurityRecord]] = {}
        for rec in records:
            if rec.valid_to is not None and rec.valid_to < rec.valid_from:
                raise ValueError(f"Invalid PIT interval for {rec.ticker}: {rec.valid_from}..{rec.valid_to}")
            bucket = by_ticker.setdefault(rec.ticker.upper(), [])
            for prev in bucket:
                prev_end = prev.valid_to or dt.date.max
                rec_end = rec.valid_to or dt.date.max
                if not (rec_end < prev.valid_from or rec.valid_from > prev_end):
                    raise ValueError(f"Overlapping PIT ticker intervals for {rec.ticker}")
            bucket.append(rec)
        self._by_ticker = by_ticker

    def resolve(self, ticker: str, as_of: dt.date) -> PITSecurityRecord | None:
        for rec in self._by_ticker.get(ticker.upper(), ()):
            end = rec.valid_to or dt.date.max
            if rec.valid_from <= as_of <= end:
                return rec
        return None


@dataclass
class PaperPositionGuardianFSM:
    """Stateful 24/5 Paper Position & Protective-Exit FSM enforcing zero naked shares."""

    open_shares: int = 0
    entry_price: Decimal = Decimal("0")
    stop_price: Decimal = Decimal("0")
    session: Literal["rth", "extended", "overnight"] = "rth"
    has_oto_stop: bool = False
    has_awake_limit_exit: bool = False
    requests_used_last_min: int = 0

    def _consume_budget(self, *, is_protective_exit: bool, count: int = 1) -> None:
        ceiling = ALPACA_PAPER_MAX_RPM if is_protective_exit else (ALPACA_PAPER_MAX_RPM - PROTECTIVE_EXIT_RESERVE_RPM)
        if self.requests_used_last_min + count > ceiling:
            raise RuntimeError(f"Broker rate budget exceeded ({self.requests_used_last_min + count} > {ceiling})")
        self.requests_used_last_min += count

    def assert_invariants(self) -> None:
        if self.requests_used_last_min > ALPACA_PAPER_MAX_RPM:
            raise AssertionError("Broker 200/min hard limit breached")
        if self.open_shares == 0:
            return
        if self.open_shares < 0:
            raise AssertionError("Negative open_shares in long guardian FSM")
        risk = (self.entry_price - self.stop_price) / self.entry_price
        if risk <= Decimal("0") or risk > Decimal(str(MAX_PROTECTIVE_STOP_PCT)):
            raise AssertionError(f"ADR-0022 stop invariant violated: risk={risk}")
        if self.session in ("rth", "overnight") and not (self.has_oto_stop or self.has_awake_limit_exit):
            raise AssertionError("Naked position in RTH/Overnight session")
        if self.session == "extended" and not self.has_awake_limit_exit:
            raise AssertionError("Extended-hours position missing awake limit exit")

    def enter_long(self, shares: int, entry_px: Decimal, stop_px: Decimal) -> None:
        if self.open_shares != 0:
            raise ValueError("Position already open")
        if shares <= 0 or entry_px <= Decimal("0"):
            raise ValueError("Invalid shares or entry_px")
        risk = (entry_px - stop_px) / entry_px
        if risk <= Decimal("0") or risk > Decimal(str(MAX_PROTECTIVE_STOP_PCT)):
            raise ValueError("Initial stop violates ADR-0022 (0, 2.00%]")
        self._consume_budget(is_protective_exit=False, count=1)
        self.open_shares = shares
        self.entry_price = entry_px
        self.stop_price = stop_px
        if self.session == "extended":
            self.has_awake_limit_exit = True
            self.has_oto_stop = False
        else:
            self.has_oto_stop = True
            self.has_awake_limit_exit = True
        self.assert_invariants()

    def add_partial_fill(self, delta_shares: int) -> None:
        if self.open_shares <= 0 or delta_shares <= 0:
            return
        # Coalesced protective-qty amend uses reserved exit budget so fills are never naked.
        self._consume_budget(is_protective_exit=True, count=1)
        self.open_shares += delta_shares
        self.assert_invariants()

    def transition_session(self, new_session: Literal["rth", "extended", "overnight"]) -> None:
        if self.open_shares > 0 and new_session == "extended" and not self.has_awake_limit_exit:
            self._consume_budget(is_protective_exit=True, count=1)
            self.has_awake_limit_exit = True
        if self.open_shares > 0 and new_session in ("rth", "overnight") and not self.has_oto_stop:
            self._consume_budget(is_protective_exit=True, count=1)
            self.has_oto_stop = True
        self.session = new_session
        self.assert_invariants()

    def ratchet_stop_up(self, new_stop_px: Decimal) -> None:
        if self.open_shares <= 0:
            return
        if new_stop_px <= self.stop_price or new_stop_px >= self.entry_price:
            return
        self._consume_budget(is_protective_exit=True, count=1)
        self.stop_price = new_stop_px
        self.assert_invariants()

    def flatten(self) -> None:
        if self.open_shares == 0:
            return
        self._consume_budget(is_protective_exit=True, count=1)
        self.open_shares = 0
        self.has_oto_stop = False
        self.has_awake_limit_exit = False
        self.assert_invariants()

    def reset_minute_window(self) -> None:
        self.requests_used_last_min = 0
        self.assert_invariants()


AUCTION_CONDITION_PRIORITY: dict[Literal["o", "c"], tuple[str, str]] = {
    "o": ("O", "Q"),
    "c": ("6", "M"),
}


@dataclass(frozen=True, slots=True)
class AuctionPrintCandidate:
    venue: str
    price: float
    size: int
    condition: str
    event_ts_ns: int


def select_listing_exchange_auction_print(
    *,
    side: Literal["o", "c"],
    prints: Sequence[AuctionPrintCandidate],
) -> AuctionPrintCandidate | None:
    """Select canonical opening/closing auction print harvested from movers/auctions.py."""
    if side not in AUCTION_CONDITION_PRIORITY:
        raise ValueError(f"side must be 'o' or 'c', got {side!r}")

    valid = [
        p
        for p in prints
        if not isinstance(p.price, bool)
        and math.isfinite(p.price)
        and p.price > 0.0
        and not isinstance(p.size, bool)
        and p.size > 0
        and p.venue
    ]
    for cond in AUCTION_CONDITION_PRIORITY[side]:
        matching = [p for p in valid if p.condition == cond]
        if matching:
            return min(matching, key=lambda p: (-p.size, p.venue, p.event_ts_ns))
    return None


def check_one_writer_symbol_isolation(
    *,
    symbol: str,
    writer_lane_id: str,
    open_position_lanes: Mapping[str, str],
    open_order_lanes: Mapping[str, str],
    is_blind_close_position: bool = False,
) -> None:
    """Enforce one-writer-per-symbol isolation harvested from movers/DECISIONS.md."""
    sym = symbol.strip().upper()
    lane = writer_lane_id.strip()
    if not sym or not lane:
        raise ValueError("symbol and writer_lane_id must be non-empty")
    if is_blind_close_position:
        raise PermissionError(
            f"Blind whole-symbol close_position on {sym} is hard-refused; act only on own order/tranche IDs"
        )
    pos_owner = open_position_lanes.get(sym)
    if pos_owner is not None and pos_owner != lane:
        raise PermissionError(f"Symbol {sym} position is owned by lane {pos_owner!r}; writer {lane!r} is hard-refused")
    ord_owner = open_order_lanes.get(sym)
    if ord_owner is not None and ord_owner != lane:
        raise PermissionError(
            f"Symbol {sym} has open order owned by lane {ord_owner!r}; writer {lane!r} is hard-refused"
        )
