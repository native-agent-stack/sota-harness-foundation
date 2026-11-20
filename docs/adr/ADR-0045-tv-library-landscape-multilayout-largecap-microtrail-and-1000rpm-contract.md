# ADR-0045: Finalized TradingView Library Landscape, 5-Layout Multi-Surface Manifest, Large-Cap `6–14 bps` Micro-Trail, Fast Sell & Re-Entry, and `1,000 req/min` Lossless Contract

- **Status:** Accepted
- **Date:** 2026-11-20
- **Layer:** L2 / L4 / L6 / L8 / L9 / L10 / L12 (`T1–T8` TradingView Library Governance, Multi-Layout Coordination, Large-Cap Ultra-Minimal Trailing, Fast Re-Entry & `1,000 req/min` Firewall)
- **Evidence Grade:** E4 (`src/cc_sota_harness/tv_multilayout_lossless_contract.py`, `tests/test_tv_multilayout_lossless_contract.py` with `2,500` Hypothesis property examples + deterministic unit/firewall tests, `run_redteam_firewall_audit` `0` findings, `45/45` MADR 4.0 ADRs, `ruff` + `ty` + `gitleaks` `0` leaks)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/tradingview/lightweight-charts, https://github.com/finos/perspective, https://github.com/OpenBB-finance/backends-for-openbb, https://github.com/nautechsystems/nautilus_trader, https://github.com/nkaz001/hftbacktest, https://github.com/vercel-labs/agent-desktop, https://github.com/deepentropy/tvscreener, https://github.com/PyneSys/pynecore, https://github.com/LuxAlgo/PineTS, https://github.com/louisnw01/lightweight-charts-python
- **Revisit Trigger:** `2026-12-06` `21:00 ET` `23/5` SIP cutover (UTP 2026-24 / SEC 34-105780), TradingView Cloud MCP tool-schema changes, Lightweight Charts `v5.x` major bump, or any change to `ADR-0022 <= 2.00%` / `6–14 bps` large-cap trailing invariants.

## Context and Problem Statement

While `sota-mover-ranker` (`ADR-0062`–`ADR-0065`) established the `LosslessProtectionKernel`, 6 uncapped TradingView presets (`[P][L][M][B][S][O]`), OpenBB Workspace backend, and `ADR-0064` strategy quarantine, the cross-repository open-core foundation (`sota-harness-foundation`) lacked one executable, SHA-256-sealed contract unifying:

1. **Advanced TradingView Library Landscape Governance:** Distinguishing pinned Apache-2.0/MIT libraries (`lightweight-charts v5`, `perspective v5.9.2`, `OpenBB-finance/backends-for-openbb`, `nautilus_trader`, `hftbacktest`), optional read-only research surfaces (Official TradingView Cloud MCP `38` tools / `0` broker-order tools, Pine Script v6 `library()`/`request.footprint()`/`force_overlay`, `deepentropy/tvscreener`, TradingView Desktop L2 UIA), philosophy-only references (`PyneSys/pynecore`, `LuxAlgo/PineTS`, `louisnw01/lightweight-charts-python`, proprietary TradingView Advanced Charts Broker API), and **hard-refused execution SaaS relays** (`marketcalls/openalgo` AGPL-3.0, `SignalStack`, `TradersPost`, `PineConnector`, `CrossTrade`).
2. **Synchronized 5-Layout Multi-Surface Coordination:** Eliminating chart-table collisions and cross-machine layout overwrites across Stationary Noesis `DISPLAY2` (`Layout '3'`, autosave OFF), `DISPLAY1` 4K wall, `24/5` Overnight `BOATS` + VIX dock, OpenBB + Perspective + LWC v5 cockpit, and Portable Mac M5 Max failover (`Layout 'agy'`, autosave ON, `singleActiveBrokerHostOnly = true`).
3. **Large-Cap Ultra-Minimal `6–14 bps` Micro-Trail & Sub-Venue Fast-Sell / Suitable-Timing Re-Entry:** Standard `25+ bps` runner trails are too loose for ultra-liquid mega-caps (`ADV >= $500M` or `ADV >= $150M` & `ATR_1m <= 0.12%`, spread `<= 8 bps`), whereas Alpaca's native `trailing_stop` rejects `trail_percent < 0.10%` (HTTP 422). Operators need exact-`Decimal` Reg NMS Rule 612 `6–14 bps` micro-trailing (`>= 1` legal tick separation) paired with `1.1s` awake synthetic fast-sell limits (NBBO-aware green-floor preservation on attempt `0` and unimpeded `42/62 bps` urgency sweeps on retries `1..2`), coupled seamlessly with anti-chase suitable-timing Wave-2/3 re-entry (`Window A` pullback/bounce absorption + `Window B` tight coil) under an unstarvable `1,000 req/min` Alpaca / `3,000 req/min` IBKR `:4002` exit-reserve budget.

## Decision Outcome

1. **Publish Executable Contract (`src/cc_sota_harness/tv_multilayout_lossless_contract.py`):**
   - Seals all `14` audited TradingView & companion libraries (`TV_LIBRARY_LANDSCAPE_STACK`) into the `4` `ADR-0017` capability classes with `order_authority = False` and `visual_may_bind_webhook = False` on every visual/research surface.
   - Seals all `5` synchronized layouts (`CANONICAL_TV_MULTI_LAYOUTS`, `>= 92%` unobstructed candles, zero HUD anchor overlap, `singleActiveBrokerHostOnly = true`).
   - Implements `compute_largecap_micro_trail_plan()` in exact `Decimal` (Reg NMS Rule 612 `$1.00`-crossing safe, `ADR-0022 <= 2.00%`, `4x` leverage equity risk cap `<= 1.35%`, `5–10 bps` instant `BE+` arm, `6–14 bps` micro-trail width, automatic `sub_venue_micro_trail_active` detection below `venue_min_trail_bps`, green-floor-preserving fast-sell marketable limits, strict monotonicity, and `take_profit_cap_enabled = False`).
   - Implements `evaluate_suitable_timing_reentry()` for symmetric Long & `$0 ETB`/SSR Short Wave-2/3 re-entry (`Window A` `6s`/`12s` dwell + `>= 12 bps` large-cap / `>= 25 bps` standard retrace + VWAP hold + confirming OFI; `Window B` `30s..300s` tight coil; anti-chase ceilings; `max_waves = 3`; `R3a` 2-stopout lock; `-75 bps` daily scratch breaker; `ADR-0064` strategy quarantine).
   - Implements `DualLane1000RpmRateBudget` (`1,000/100` Alpaca Algo-Plus with HTTP-429 `200/20` isolated unstarvable exit reserve + `3,000/300` `50/s` IBKR `:4002` + `18/min` TV Cloud MCP delta guard) and `validate_tv_preset_and_route_firewall()` (6 uncapped `TP OFF` whole-share presets, hard-refused live-capital ports `4001`/`7496`/`8796`/`8798`, hard-refused live-capital endpoint `api.alpaca.markets`, and hard-refused SaaS execution relays).
   - Ships strictly as `PROTECTIVE_FILTER_OR_GOVERNANCE` (`standalone_alpha_claim = False`).

## Alternatives Considered

- **Routing TradingView Alerts via Third-Party SaaS (`SignalStack`, `TradersPost`, `OpenAlgo`):** Rejected — violates `ADR-0017` `HARD_REFUSED_EXECUTION_SAAS`, introduces external credential/webhook attack surfaces, and bypasses our local `ADR-0022`/`ADR-0063` exact-`Decimal` lossless kernel.
- **Relying Solely on Broker-Native `trailing_stop` for Mega-Caps:** Rejected — Alpaca's `0.10% + 1 tick` HTTP-422 floor cannot express `6–9 bps` mega-cap micro-trails; pairing the native broker catastrophe stop with `sub_venue_micro_trail_active` `1.1s` awake synthetic fast-sell limits achieves both exchange-level catastrophe safety and `6–14 bps` precision.

## Verification Witness

- `uv run pytest -q` (full suite including `tests/test_tv_multilayout_lossless_contract.py` with `2,500` Hypothesis property proofs PASS).
- `uv run ruff check . && uv run ruff format --check . && uv run ty check src/cc_sota_harness/tv_multilayout_lossless_contract.py` (`0` errors).
- `run_redteam_firewall_audit` (`0` P0–P3 findings across all `24` vulnerability classes).
- `uv run python scripts/architecture_catalog.py && uv run python scripts/architecture_catalog.py --check` (`45` ADRs valid, `0` drift) & `gitleaks protect --staged --no-banner` (`0` leaks).
