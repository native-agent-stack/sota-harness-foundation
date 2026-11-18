# ADR-0012: L11 / T0–T8 SOTA Extreme-Mover Trading Stack, Study Wall & PC Cleanup

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L11` Trading System Stack (`T0–T8`) & Machine Hygiene
- **Evidence Grade:** E3 (18 Pinned Clones + 13-Tool MCP + Quant Suite Verified)
- **Revisit Trigger:** 2027-01-01 or owner-authorized study-wall / broker-lane amendment

## Context and Problem Statement

Building and compounding the US-equities extreme-mover system requires strict alignment between research (`movers`, `tsl`), event-driven simulation (`meridian` on `nautilus_trader` `v2.0.0rc9`), live `3.0s` SIP+BOATS scanning (`sota-mover-ranker`), and `200 req/min` Alpaca Paper + `3,000 req/min` IBKR Paper autonomous execution — while retiring superseded scratch folders, broken LaunchAgents, and backup clutter across the Mac.

## Decision Outcome

1. **18-Repo Pinned Upstream Shelf (`~/Documents/upstream/PINS.md`):** Verified on every commit and test run against exact 40-char Git SHAs (`alpaca-py` `v0.45.0`, `alpaca-mcp-server` `v2.4.1`, `nautilus_trader` `v2.0.0rc9`, `nautilus-alpaca`, `polars` `py-2.1.0`, `duckdb` `v2.0.0`, `edgartools` `v6.2.0`, `ml4t-diagnostic` `v0.2.0`, `skfolio` `v1.12.7`, `hftbacktest`, `ib_async` `v2.1.0`, `perspective` `v5.9.2`, `lightweight-charts`, `quantstats`, `vectorbt` `v1.2.0`, `pandera` `v0.35.0`, `exchange_calendars` `4.13.2`, `statsmodels` `v0.15.0`).
2. **Hard Quantitative & Execution Invariants (`src/cc_sota_harness/gates.py`):**
   - **Study Wall (`<= 2026-10-15`):** Calibration, feature selection, `CombinatorialPurgedCV`, and `Deflated Sharpe Ratio` (`DSR`) strictly observe `<= 2026-10-15`; `>= 2026-10-16` is frozen forward evaluation only.
   - **Paper Execution & Mandatory Exit Protection:** Paper (`PA*` `<= 200 req/min` with `15/min` protective-exit reserve; `DU*` `<= 3,000 msg/min`) is never gated, caps initial stop distance at `<= 2.00%` (`ADR-0022`), enforces monotonic ratchet-only trails, requires `OTO`/`gtc` broker stops in regular/overnight hours and awake `extended_hours` limit exits `24/5`, and hard-refuses live accounts.
3. **4-Server Lean SOTA MCP Bridge (`.mcp.json`):** Connects `sota-mover-ranker` (`13` tools), `sota-peer-bus` (`6` tools), `agy-sota-core` (`5` tools), and `codebase-memory` (`v0.12.1`) within the `<= 6` lean MCP server budget.
4. **PC Superseded Artifact Retirement:**
   - Unload & remove superseded `~/Library/LaunchAgents/com.trading-sota.ranking-daily.plist` (failing `exit 126` under macOS TCC and superseded by Orca schedules + `sota-mover-ranker`).
   - Purge superseded `.replaced-*`, `.bak*`, `.swp`, and `.trash` files across `~`, `~/.claude`, Orca's Claude profile, `~/.codex`, and `~/.claude/canon/`, plus stale `>2h` Canon scratch runs in `/private/tmp`, duplicate `~/docs/plugin-landscape`, and empty `~/orca/workspaces/{canon,trading-sota,tsl}` — while preserving `~/canon` (`sip-history-dev` Parquet catalog), `~/Documents/market-data`, `~/Documents/upstream`, and all active repositories untouched.

## Alternatives Considered

- **`ranaroussi/yfinance`, `shner-elmo/TradingView-Screener`, `deepentropy/tvscreener`, `Mathieu2301/TradingView-API`:** Rejected across `tsl` and `sota-mover-ranker` (non-PIT, missing SIP/BOATS condition codes, or undocumented TradingView scraping).
- **`HKUDS/AI-Trader`, `HKUDS/Vibe-Trading`, `TraderAlice/OpenAlice`, `NoFxAiOS/nofx`:** Rejected for execution; daily/consumer LLM bots lack sub-minute protective stops, PIT provenance, and `200 req/min` broker pacing reserves.
- **Deleting `~/canon` or `~/Documents/trading-sota` outright on disk:** Rejected; `~/canon` holds the `sip-history-dev` Parquet catalog read by `movers`, and `trading-sota` holds historical run receipts cited by `tsl`. Both are removed from Orca's active sidebar while remaining read-only archives on disk.

## Verification Witness

- `doctor.py` (`0` errors across all 4 MCP servers, 18 upstream clones, 34 plugins, and 20 `mise` binaries) + `pytest -v` (`test_t1_t4_quant_stack_e2e`, `test_paper_order_intent_and_live_refusal`, `test_property_ratchet_never_loosens_stop`).
