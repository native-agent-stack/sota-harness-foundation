"""Upstream-First Shared Active 24/5 Lossless Foundation & Dual-Machine Merit Contract (`ADR-0040`).

Guarantees three foundational invariants across the entire dual-machine (`Mac M5 Max <-> Noesis`) stack:
1. **Upstream-First, Zero Reinvention:** Every layer integrates or builds directly upon pinned maintained SOTA
   upstream platforms/libraries (`polars`, `duckdb`, `vectorbt`, `skfolio`, `ml4t-diagnostic`, `nautilus_trader`,
   `hftbacktest`, `alpaca-py`, `alpaca-mcp-server`, `ib_async`, `edgartools`, `quantstats`, `pandera`,
   `exchange_calendars`, `perspective`, `lightweight-charts`, `orca`, `hcom`, `beads`, `qmd`).
2. **Paper == Live Active 24/5 Foundation:** All 4 Paper accounts (`3` Alpaca Paper `:8799/:8787/:8797` + `1` IBKR
   Paper `:4002`) and Stage-5 Lossless Live (`:8798`) run on the exact same `24/5` Lossless Foundation (`ADR-0022
   <= 2.00%` stop, `ADR-0024` runner floor, `100/min` reserved protective-exit budget, `50%` fast-harvest + `Wave-2`
   re-entry, `:8799` Extended-Hours/BOATS guardian, `-1.50%` daily breaker, zero PII/USD leaks).
3. **Never-Gated Merit Sources -> Proven-Only Automated Live:** Sim (`S1/S2`) and all `4` Paper accounts are
   strictly `NEVER_GATED`; Stage-5 Live (`:8798`) runs automated proven strategies starting with the Shared
   Lossless Foundation.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from cc_sota_harness.gates import MAX_PROTECTIVE_STOP_PCT, STUDY_WALL

SHARED_FOUNDATION_SCHEMA_VERSION = "sota-shared-24x5-merit-foundation.v1"
DUAL_MACHINE_MERIT_GOAL_ID = "G_SOTA_DUAL_MACHINE_MERIT_TO_LOSSLESS_LIVE_24X5"
MAX_STOP_ADR0022_PERCENT_POINTS = round(MAX_PROTECTIVE_STOP_PCT * 100.0, 4)  # 0.02 decimal -> 2.00%

UPSTREAM_PLATFORM_BINDINGS: dict[str, dict[str, Any]] = {
    "market_data_and_pit_feeds": {
        "mode": "integrate_and_build_on",
        "upstreams": ("alpaca-py", "ib_async", "edgartools", "exchange_calendars", "polars", "duckdb", "pandera"),
        "policy": "Zero custom calendar/CSV/SEC parsers; strict bitemporal PIT <= 2026-10-15 pre-wall.",
    },
    "backtest_and_statistical_falsification_s1": {
        "mode": "integrate_and_build_on",
        "upstreams": ("vectorbt", "skfolio", "ml4t-diagnostic", "quantstats", "statsmodels"),
        "policy": "Use skfolio CombinatorialPurgedCV, ml4t-diagnostic DSR/PBO, HLZ t*(N), 1x/2x Almgren-Chriss.",
    },
    "event_and_queue_microstructure_sim_s2": {
        "mode": "integrate_and_build_on",
        "upstreams": ("nautilus_trader", "hftbacktest"),
        "policy": "Use NautilusTrader v2.0.0rc9 & hftbacktest RiskAdverseQueueModel (-n 8) on Noesis-Carbon WSL2.",
    },
    "active_24x5_paper_and_live_execution": {
        "mode": "integrate_and_build_on",
        "upstreams": ("alpacahq/alpaca-mcp-server==2.4.1", "ib_async", "sota-dynamic-trail-c"),
        "policy": "Shared 24/5 Lossless Foundation across 3 Alpaca Paper + 1 IBKR Paper (NEVER GATED) and :8798 Live (PROVEN ONLY).",
    },
    "visualization_and_institutional_telemetry": {
        "mode": "integrate_and_build_on",
        "upstreams": ("perspective", "lightweight-charts", "TradingView Pine v6"),
        "policy": "FINOS Perspective blotter + TradingView Lightweight Charts + non-repainting Pine v6 HUD.",
    },
    "dual_machine_orchestration_and_memory": {
        "mode": "integrate_and_build_on",
        "upstreams": (
            "stablyai/orca",
            "Yeachan-Heo/oh-my-claudecode",
            "Yeachan-Heo/oh-my-codex",
            "aannoo/hcom",
            "gastownhall/beads",
            "tobi/qmd",
        ),
        "policy": "Native Gemini run_workflow WF20 <-> cc-lead OMC v2 <-> Codex OMX <-> DSH <-> Dual-Machine Orca Automations.",
    },
}

SHARED_24X5_LOSSLESS_FOUNDATION: dict[str, Any] = {
    "schema_version": SHARED_FOUNDATION_SCHEMA_VERSION,
    "goal_id": DUAL_MACHINE_MERIT_GOAL_ID,
    "paper_and_live_share_same_foundation": True,
    "always_on_24x5": True,
    "dec6_2026_23x5_sip_ready": True,
    "adr0022_max_initial_stop_pct": MAX_STOP_ADR0022_PERCENT_POINTS,
    "adr0024_runner_floor_formula": "min(2.00%, max(0.72%, 1.15 * prewall_p85))",
    "fast_core_harvest_fraction": 0.50,
    "wave2_reentry_min_cooldown_sec": 6.0,
    "protective_exit_reserve_pct": 10.0,
    "daily_drawdown_breaker_pct": -1.50,
    "zero_pii_and_usd_telemetry": True,
    "study_wall_iso": STUDY_WALL.isoformat(),
    "active_mac_ports": {
        "P1_Account_C_Lossless_Mirror": 8799,
        "P2_Account_B_Balanced_Ranker": 8787,
        "P3_Account_A_Aggressive_Crucible": 8797,
        "P4_Account_D_IBKR_Institutional": 4002,
        "L5_Stage5_Lossless_Live": 8798,
    },
}


@dataclass(frozen=True)
class LaneFoundationCheck:
    lane_id: str
    tier: str  # "SIM" | "PAPER" | "LIVE"
    gating_policy: str
    shares_lossless_foundation: bool
    max_stop_pct: float
    protective_exit_reserve_pct: float
    upstream_backed: bool = True


def validate_lane_foundation_contract(cfg: LaneFoundationCheck) -> tuple[bool, list[str]]:
    """Fail-closed validation of Sim/Paper NEVER-GATED and Live Proven-Only Shared Foundation invariants."""
    errors: list[str] = []
    if not cfg.upstream_backed:
        errors.append("UPSTREAM_FIRST_VIOLATION:custom_reinvention_forbidden")
    if not cfg.shares_lossless_foundation:
        errors.append("SHARED_24X5_LOSSLESS_FOUNDATION_REQUIRED")
    if (
        isinstance(cfg.max_stop_pct, bool)
        or not math.isfinite(cfg.max_stop_pct)
        or not (0.0 < cfg.max_stop_pct <= MAX_STOP_ADR0022_PERCENT_POINTS)
    ):
        errors.append(f"ADR0022_STOP_VIOLATION:{cfg.max_stop_pct}")
    if (
        isinstance(cfg.protective_exit_reserve_pct, bool)
        or not math.isfinite(cfg.protective_exit_reserve_pct)
        or cfg.protective_exit_reserve_pct < 10.0
    ):
        errors.append(f"EXIT_RESERVE_BELOW_10PCT:{cfg.protective_exit_reserve_pct}")

    tier_u = cfg.tier.upper()
    if tier_u in ("SIM", "PAPER"):
        if cfg.gating_policy != "NEVER_GATED":
            errors.append(f"SIM_AND_PAPER_MUST_BE_NEVER_GATED:got={cfg.gating_policy}")
    elif tier_u == "LIVE":
        if cfg.gating_policy != "PROVEN_AUTOMATION_ONLY_STARTING_WITH_LOSSLESS_FOUNDATION":
            errors.append(f"LIVE_MUST_BE_PROVEN_AUTOMATION_ONLY:got={cfg.gating_policy}")
    else:
        errors.append(f"UNKNOWN_TIER:{cfg.tier}")
    return (len(errors) == 0), errors


def build_shared_foundation_manifest() -> dict[str, Any]:
    """Build deterministic SHA-256 manifest of the Shared 24/5 Lossless Foundation & Upstream Platform Bindings."""
    body: dict[str, Any] = {
        "schema_version": SHARED_FOUNDATION_SCHEMA_VERSION,
        "adr": "ADR-0040",
        "goal_id": DUAL_MACHINE_MERIT_GOAL_ID,
        "shared_24x5_foundation": SHARED_24X5_LOSSLESS_FOUNDATION,
        "upstream_platform_bindings": UPSTREAM_PLATFORM_BINDINGS,
        "upstream_domains_count": len(UPSTREAM_PLATFORM_BINDINGS),
    }
    body["foundation_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=list).encode()).hexdigest()
    return body
