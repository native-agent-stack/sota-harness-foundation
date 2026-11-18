"""Two-Stage Lit Round-Lot Passive Queue (`15s`) -> `<= 10.0 bps` Marketable Collar (`H095`).

Implements the deterministic execution invariants for pre-registered Trial #95
(`H095_TWO_STAGE_LIT_QUEUE_15S_TO_10BPS_MARKETABLE_COLLAR_ORB_CPCV`,
`spec_sha256 = 5abe51a4caacf4bf6955a331b495310fae1791a8d74a76c111bc9e6a35b5f4fa`,
`t*(95) = 4.1858`):
1. Stage 1 (`[ns_entry, ns_entry + 15s]`): Rest passive L1 buy limit at `bp_entry` on the strict
   lit round-lot queue (`x != 'D'`, non-`'I'`, `s >= 100`) via `RiskAdverseQueueModel`.
2. Stage 2 (`t = ns_entry + 15s`): If Stage 1 has not filled, escalate to a marketable limit collar
   at `ap_15s` if and only if `ap_15s <= ap_entry * 1.0010` (`<= +10.0 bps` ask drift), live NBBO
   spread `<= 10.0 bps`, and `as_15s * 100.0 >= order_qty_shares`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from cc_sota_harness.passive_bid_trail_prewall import (
    CTA_UTP_ROUND_LOT_SHARES,
    QuoteTickNs,
    TradePrintNs,
    simulate_passive_bid_orb_fill,
)

H095_HYPOTHESIS_ID = "H095_TWO_STAGE_LIT_QUEUE_15S_TO_10BPS_MARKETABLE_COLLAR_ORB_CPCV"
H095_TRIAL_N = 95
H095_SPEC_SHA256 = "5abe51a4caacf4bf6955a331b495310fae1791a8d74a76c111bc9e6a35b5f4fa"
H095_STAGE1_TTL_NS = 15_000_000_000
H095_MAX_COLLAR_DRIFT_BPS = 10.0
H095_MAX_LIVE_SPREAD_BPS = 10.0


@dataclass(frozen=True, slots=True)
class TwoStageHybridFillResult:
    filled: bool
    fill_stage: str
    fill_px: float | None
    fill_ts_ns: int | None
    ask_drift_15s_bps: float
    spread_15s_bps: float


def is_lit_roundlot_queue_trade(exchange_code: str, conditions: Sequence[str], size_shares: float) -> bool:
    """Exclude off-exchange TRF (`x == 'D'`), odd-lot (`'I'`), and `< 100` share prints from L1 queue depletion."""
    if not math.isfinite(size_shares) or size_shares < CTA_UTP_ROUND_LOT_SHARES:
        return False
    if str(exchange_code).strip().upper() == "D":
        return False
    return "I" not in conditions


def simulate_h095_two_stage_hybrid_orb_fill(
    *,
    ns_entry: int,
    bp_entry: float,
    bs_entry_lots: float,
    ap_entry: float,
    order_qty_shares: float,
    lit_roundlot_trades: Sequence[TradePrintNs],
    post_entry_quotes: Sequence[QuoteTickNs],
    entry_hhmm_et: str = "0935",
    stage1_ttl_ns: int = H095_STAGE1_TTL_NS,
    max_collar_drift_bps: float = H095_MAX_COLLAR_DRIFT_BPS,
    max_live_spread_bps: float = H095_MAX_LIVE_SPREAD_BPS,
) -> TwoStageHybridFillResult:
    """Simulate `H095` 2-stage (`15s` strict lit passive -> `<= 10.0 bps` marketable collar) fill."""
    if (
        not (
            math.isfinite(bp_entry)
            and math.isfinite(bs_entry_lots)
            and math.isfinite(ap_entry)
            and math.isfinite(order_qty_shares)
            and math.isfinite(max_collar_drift_bps)
            and math.isfinite(max_live_spread_bps)
        )
        or bp_entry <= 0.0
        or ap_entry < bp_entry
        or bs_entry_lots < 0.0
        or order_qty_shares <= 0.0
        or stage1_ttl_ns <= 0
    ):
        raise ValueError("Invalid H095 two-stage hybrid fill inputs")
    if len(entry_hhmm_et) != 4 or not entry_hhmm_et.isdigit():
        raise ValueError(f"entry_hhmm_et must be 4-digit HHMM, got {entry_hhmm_et!r}")

    if entry_hhmm_et >= "1550":
        return TwoStageHybridFillResult(
            filled=False,
            fill_stage="blocked_late_rth",
            fill_px=None,
            fill_ts_ns=None,
            ask_drift_15s_bps=0.0,
            spread_15s_bps=0.0,
        )

    ns_cutoff = ns_entry + stage1_ttl_ns
    t_s1 = [tr for tr in lit_roundlot_trades if ns_entry < tr.ts_ns <= ns_cutoff]
    q_s1 = [qt for qt in post_entry_quotes if ns_entry < qt.ts_ns <= ns_cutoff]

    s1_res = simulate_passive_bid_orb_fill(
        limit_bid_px=bp_entry,
        initial_bid_lots=bs_entry_lots,
        order_qty_shares=order_qty_shares,
        trades=t_s1,
        quotes=q_s1,
    )
    if s1_res.filled and s1_res.fill_px is not None and s1_res.fill_ts_ns is not None:
        return TwoStageHybridFillResult(
            filled=True,
            fill_stage=f"stage1_passive_{s1_res.fill_reason}",
            fill_px=s1_res.fill_px,
            fill_ts_ns=s1_res.fill_ts_ns,
            ask_drift_15s_bps=0.0,
            spread_15s_bps=0.0,
        )

    # Causal quote at t <= ns_entry + 15s (fallback to entry quote if no quote arrived in (ns_entry, ns_cutoff])
    if q_s1:
        q15 = max(q_s1, key=lambda qt: qt.ts_ns)
        bp_15, ap_15, as_15 = q15.bid_px, q15.ask_px, q15.ask_lots
    else:
        bp_15, ap_15, as_15 = bp_entry, ap_entry, 0.0

    mid_15 = 0.5 * (bp_15 + ap_15)
    if mid_15 <= 0.0 or ap_15 < bp_15:
        return TwoStageHybridFillResult(
            filled=False,
            fill_stage="collar_rejected_invalid_quote",
            fill_px=None,
            fill_ts_ns=None,
            ask_drift_15s_bps=0.0,
            spread_15s_bps=0.0,
        )

    spread_15_bps = ((ap_15 - bp_15) / mid_15) * 10_000.0
    ask_drift_15_bps = ((ap_15 / ap_entry) - 1.0) * 10_000.0
    max_ask_px = ap_entry * (1.0 + max_collar_drift_bps / 10_000.0)

    if (
        ap_15 <= max_ask_px + 1e-9
        and 0.0 < spread_15_bps <= max_live_spread_bps + 1e-9
        and (as_15 * CTA_UTP_ROUND_LOT_SHARES) + 1e-9 >= order_qty_shares
    ):
        return TwoStageHybridFillResult(
            filled=True,
            fill_stage="stage2_collar_15s",
            fill_px=ap_15,
            fill_ts_ns=ns_cutoff,
            ask_drift_15s_bps=round(ask_drift_15_bps, 4),
            spread_15s_bps=round(spread_15_bps, 4),
        )

    return TwoStageHybridFillResult(
        filled=False,
        fill_stage="collar_rejected",
        fill_px=None,
        fill_ts_ns=None,
        ask_drift_15s_bps=round(ask_drift_15_bps, 4),
        spread_15s_bps=round(spread_15_bps, 4),
    )
