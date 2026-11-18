"""Core quantitative & execution-protection invariants for SOTA trading system builds.

Enforces:
- Study Wall (<= 2026-10-15 for calibration/selection; >= 2026-10-16 frozen forward-only)
- ADR-0022 Protective Stop & Monotonic Ratchet (<= 2.00% exact Decimal cap, finite prices, no naked positions)
- Paper Broker Pacing (<= 200 req/min Alpaca Paper with 15/min protective-exit reserve; <= 3,000 msg/min IBKR Paper)
- Hard Live-Account Refusal (only PA* or DU* paper venues permitted)
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from decimal import Decimal

STUDY_WALL = dt.date(2026, 10, 15)
MAX_PROTECTIVE_STOP_PCT = 0.02
MAX_PROTECTIVE_STOP_DEC = Decimal("0.02")
ALPACA_PAPER_MAX_RPM = 200
PROTECTIVE_EXIT_RESERVE_RPM = 15
IBKR_PAPER_MAX_MPM = 3000
IBKR_PROTECTIVE_EXIT_RESERVE_MPM = 300


@dataclass(frozen=True)
class OrderIntent:
    venue_prefix: str
    symbol: str
    side: str
    entry_price: float
    stop_price: float
    session: str  # "rth" | "premarket" | "afterhours" | "overnight"
    has_broker_oto_stop: bool
    has_awake_limit_exit: bool
    requests_used_last_min: int
    is_protective_exit: bool = False


def check_study_wall(trade_date: dt.date, *, stage: str) -> None:
    """Fail-closed study wall: calibration/selection cannot touch dates > 2026-10-15."""
    if stage not in {"calibration", "forward"}:
        raise ValueError(f"unknown stage '{stage}'; expected 'calibration' or 'forward'")
    if stage == "calibration" and trade_date > STUDY_WALL:
        raise ValueError(
            f"study-wall violation: {trade_date.isoformat()} > {STUDY_WALL.isoformat()} during calibration"
        )
    if stage == "forward" and trade_date <= STUDY_WALL:
        raise ValueError(f"forward-record violation: {trade_date.isoformat()} <= {STUDY_WALL.isoformat()}")


def check_paper_order_intent(intent: OrderIntent) -> None:
    """Fail-closed validation of paper-only execution, pacing reserve, and exact Decimal <=2.00% protection."""
    if intent.venue_prefix not in {"PA", "DU"}:
        raise PermissionError(f"live or unrecognized venue prefix '{intent.venue_prefix}' is hard-refused")
    if not intent.symbol or intent.symbol.upper() in {"QQQ", "SPY", "IWM"}:
        raise ValueError(f"invalid extreme-mover candidate symbol '{intent.symbol}'")
    if (
        not (math.isfinite(intent.entry_price) and math.isfinite(intent.stop_price))
        or intent.entry_price <= 0.0
        or intent.stop_price <= 0.0
    ):
        raise ValueError("entry_price and stop_price must be finite and strictly positive")

    max_rpm = ALPACA_PAPER_MAX_RPM if intent.venue_prefix == "PA" else IBKR_PAPER_MAX_MPM
    reserve = PROTECTIVE_EXIT_RESERVE_RPM if intent.venue_prefix == "PA" else IBKR_PROTECTIVE_EXIT_RESERVE_MPM
    entry_cap = max_rpm - reserve
    limit = max_rpm if intent.is_protective_exit else entry_cap
    if intent.requests_used_last_min >= limit:
        raise RuntimeError(f"rate-budget exceeded ({intent.requests_used_last_min} >= {limit})")

    d_entry = Decimal(str(intent.entry_price))
    d_stop = Decimal(str(intent.stop_price))
    if intent.side == "buy":
        if d_stop >= d_entry:
            raise ValueError("long stop_price must be strictly below entry_price")
        d_risk = (d_entry - d_stop) / d_entry
    elif intent.side == "sell_short":
        if d_stop <= d_entry:
            raise ValueError("short stop_price must be strictly above entry_price")
        d_risk = (d_stop - d_entry) / d_entry
    else:
        raise ValueError(f"unsupported side '{intent.side}'")

    if d_risk > MAX_PROTECTIVE_STOP_DEC:
        raise ValueError(
            f"protective stop width {float(d_risk):.4%} exceeds {MAX_PROTECTIVE_STOP_PCT:.2%} ADR-0022 cap"
        )

    if intent.session == "rth":
        if not intent.has_broker_oto_stop:
            raise ValueError("RTH entry requires atomic broker OTO/bracket stop")
    elif intent.session in {"premarket", "afterhours", "overnight"}:
        if not (intent.has_awake_limit_exit or (intent.venue_prefix == "DU" and intent.has_broker_oto_stop)):
            raise ValueError(
                f"{intent.session} position requires awake extended-hours limit exit or IBKR outsideRth stop"
            )
    else:
        raise ValueError(f"unknown session '{intent.session}'")


def ratchet_long_stop(current_stop: float, high_watermark: float, trail_pct: float) -> float:
    """Monotonic ratchet-only trailing stop for long positions (never lowers stop)."""
    if (
        not (math.isfinite(current_stop) and math.isfinite(high_watermark) and math.isfinite(trail_pct))
        or current_stop <= 0.0
        or high_watermark <= 0.0
        or not (0.0 < trail_pct <= MAX_PROTECTIVE_STOP_PCT)
    ):
        raise ValueError("invalid long ratchet inputs")
    candidate = high_watermark * (1.0 - trail_pct)
    return max(current_stop, candidate)


def ratchet_short_stop(current_stop: float, low_watermark: float, trail_pct: float) -> float:
    """Monotonic ratchet-only trailing stop for short positions (never raises stop)."""
    if (
        not (math.isfinite(current_stop) and math.isfinite(low_watermark) and math.isfinite(trail_pct))
        or current_stop <= 0.0
        or low_watermark <= 0.0
        or not (0.0 < trail_pct <= MAX_PROTECTIVE_STOP_PCT)
    ):
        raise ValueError("invalid short ratchet inputs")
    candidate = low_watermark * (1.0 + trail_pct)
    return min(current_stop, candidate)
