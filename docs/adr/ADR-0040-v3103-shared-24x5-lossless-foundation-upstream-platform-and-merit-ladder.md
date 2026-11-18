# ADR-0040: `v3.10.3` Upstream-First Shared Active `24/5` Lossless Foundation (`Paper` == `Live` Engine) & Dual-Machine Merit-Promotion Contract

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0 / L2 / L3 / L6 / L8 / L9 (`T1–T5` × `H0–H7` — Shared 24/5 Execution Foundation & Upstream-First Zero-Reinvention)
- **Evidence Grade:** E4 (`40` ADRs, `src/cc_sota_harness/shared_24x5_merit_foundation.py`, `tests/test_shared_24x5_merit_foundation.py`, `pytest` + Hypothesis + `ruff` + `gitleaks` `0` Leaks)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/sota-multi-model-workflows, https://github.com/alpacahq/alpaca-mcp-server, https://github.com/nautechsystems/nautilus_trader, https://github.com/nkaz001/hftbacktest, https://github.com/skfolio/skfolio, https://github.com/ml4t/diagnostic, https://github.com/stablyai/orca
- **Revisit Trigger:** `2026-12-06` `23/5` Consolidated SIP cutover or `v4.0.0` upstream shelf bump

## Context and Problem Statement

1. **Single Active `24/5` Lossless Foundation Shared by Paper and Live:** Paper accounts (`3` distinct Alpaca Paper `:8799/:8787/:8797` + `1` IBKR Paper `:4002`) and the Stage-5 Lossless Live lane (`:8798`) must execute on the **exact same active `24/5` protection & execution foundation** (`ADR-0022 <= 2.00%` stop, `ADR-0024` dynamic runner floor, `100/min` reserved protective-exit budget, `50%` Core fast-harvest + `Wave-2` pullback re-entry, `:8799` Extended-Hours/BOATS guardian, `-1.50%` daily breaker, zero PII/USD leaks). The sole separator between Paper and Live is empirical merit graduation (`Sim -> P3 -> P2/P4 -> P1 -> L5`) and the owner's live window — never divergent codebases.
2. **Ungated Sim/Paper Merit Sources + Zero-Reinvention Upstream Platform Anchor:** Sim (`S1` Noesis Win32 `64c/RTX4090`, `S2` Noesis-Carbon WSL2) and all `4` Paper accounts must remain **`NEVER_GATED`**, built cleanly on top of our `18` pinned maintained upstream SOTA libraries (`polars`, `duckdb`, `vectorbt`, `skfolio`, `ml4t-diagnostic`, `nautilus_trader`, `hftbacktest`, `alpaca-py`, `alpaca-mcp-server`, `ib_async`, `edgartools`, `quantstats`, `pandera`, `exchange_calendars`, `perspective`, `lightweight-charts`, `orca`, `hcom`, `beads`, `qmd`) rather than reinventing core infrastructure.

## Decision Outcome

1. Add `src/cc_sota_harness/shared_24x5_merit_foundation.py` exporting:
   - `UPSTREAM_PLATFORM_BINDINGS` (strict upstream-first mapping across Data, Backtest/CPCV/DSR, Event/Queue Sim, Paper/Live Execution, Telemetry & Dual-Machine Orchestration).
   - `SHARED_24X5_LOSSLESS_FOUNDATION` (canonical shared `24/5` engine contract inherited by both Paper Farm and Stage-5 Live).
   - `DUAL_MACHINE_MERIT_GOAL_ID = "G_SOTA_DUAL_MACHINE_MERIT_TO_LOSSLESS_LIVE_24X5"` and fail-closed `validate_lane_foundation_contract()` / `build_shared_foundation_manifest()`.
2. Export all public contracts from `src/cc_sota_harness/__init__.py` and verify via `tests/test_shared_24x5_merit_foundation.py`.

## Alternatives Considered

- **Building separate execution/protection codepaths for Paper vs. Live or writing custom backtest/queue engines from scratch:** Rejected — violates upstream-first zero-reinvention discipline and creates paper-to-live parity drift.

## Verification Witness

- `uv run python scripts/architecture_catalog.py --check` (`40 ADRs valid, 0 drift`).
- `uv run pytest -q && mise exec -- ruff check . && mise exec -- gitleaks git --no-banner` (`PASS`, `0` leaks).
