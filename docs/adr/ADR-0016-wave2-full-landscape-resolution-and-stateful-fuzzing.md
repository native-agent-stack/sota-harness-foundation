# ADR-0016: Wave-2 Full Landscape SOTA Resolution — Adversarial Remediation, Starred Gap Closure & Stateful Fuzzing

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** L0 / L1 / L4 / L6 / L8 / L9 / L11 (`T1–T6`)
- **Evidence Grade:** E4
- **Revisit Trigger:** `2026-12-06` 23/5 Consolidated SIP go-live confirmation or `nautilus_trader` upstream pin bump beyond `v2.0.0rc9`

## Context and Problem Statement

Wave-1 multi-model execution across four independent Orca worker runtimes (`Antigravity` `gemini-4-carbon-high`, `Codex` `gpt-6.2-astra` `max`, `OpenCode 2.3.0 + OMO 5.1.75`, and `Claude Sonnet 5.5` + `OMP`) plus our 404-repo starred audit surfaced concrete findings requiring clean convergence:
1. **20 Adversarial Harness `xfail` Witnesses (`codex-astra-audit`):** `NaN`/`Inf` order/ratchet inputs, `1e-9` float stop-cap overshoot on cent grids (`$250,000.49`), mixed pre-wall/post-wall `forward` batches, `7 bps` float stop-touch under-rounding (`$99.92999999999999` vs `$99.93`), `t=0` crossed entry bids, split midpoint denominators, and `1e308` midpoint sum overflow.
2. **CTA/UTP ISO Condition Code (`Peer Msg #12`):** In `alpaca-sip/raw/meta/codes.json`, `'F'` denotes Intermarket Sweep Order (`ISO`) whereas `'I'` denotes Odd Lot Trade.
3. **Upstream `ExitGate` Provenance (`omo-opencode-exec`):** Pinned `nautilus_trader@da6b57ae` exposes `SpreadAnalyzer` and `ContingencyType.OTO=2` (mirrored in `upstream_execution_parity.py`) but contains no `ExitGate` symbol (`UPSTREAM_SYMBOL_UNVERIFIED`).
4. **Remaining Starred & Institutional Gaps:** Offline CVE lockfile scanning (`aquasecurity/trivy`), subscription-CLI proxy (`router-for-me/CLIProxyAPI`), SEC PDF/exhibit ingestion (`microsoft/markitdown`), visual plan annotation (`backnotprop/plannotator`), square-root market impact, flag-gated `2026-12-06` `23/5` SIP + nanosecond `BOATS` freshness, Point-in-Time (`PIT`) ticker-reuse protection, and stateful Hypothesis order-lifecycle fuzzing.

## Decision Outcome

We resolve all Wave-1 adversarial findings and close the Wave-2 starred + institutional gaps in one verified convergence:

1. **Zero-`xfail` Harness Remediation (`gates.py` & `microstructure_h05.py`):**
   - Enforce exact `Decimal` `<= 2.00%` stop-width arithmetic, strict `math.isfinite` order/ratchet/feature validation, dual `min_date`/`max_date` study-wall gates, exact `Decimal` basis-point stop triggers including `t=0` atomic entry checks, overflow-safe midpoint math on unified `entry_ask` notional, `[0.0, 1.0]` probability bounds with `H05_HLZ_T_HURDLE` floor, and `is_cta_utp_iso_print` (`'F'` = ISO, `'I'` = Odd Lot). All 20 harness `xfail`s in `tests/test_adversarial_h05.py` are promoted to strict `PASS` regression gates.
2. **Pinned Upstream Execution Parity (`upstream_execution_parity.py`):**
   - Merge `SpreadAnalyzerParity`, `RiskAdverseQueueModel`, `ProbQueueModel` (`LogProbQueueModel2` + 4 sibling probability kernels), Rust half-away tick rounding, and `ContingencyType.OTO=2` with 24 unit tests (`tests/test_upstream_execution_parity.py`).
3. **Wave-2 Starred Toolchain & Plugin Closure (`45` `mise` Tools, `27` Verified CLIs, `40` Plugins across `18` Marketplaces):**
   - Lock `trivy@0.76.2` (`L9` vulnerability/misconfig scanner), `github:router-for-me/CLIProxyAPI@8.0.75` (`cli-proxy-api`, `L4` subscription-CLI OpenAI/Anthropic proxy), `markitdown@0.1.9` (`L6`/`T2` SEC Exhibit PDF-to-Markdown CLI), and `plannotator@plannotator` (`L1` visual plan annotation plugin).
4. **Institutional Frontier Modules (`src/cc_sota_harness/institutional_frontier.py`):**
   - Land `almgren_chriss_sqrt_impact_bps` (square-root bucket participation + borrow carry), flag-gated `resolve_245_session_window` (`enable_dec6_235_sip=False` default, `XNYS` holiday/half-day `12:55 ET` flatten, `20:00–21:00 ET` ATS pause eligibility) + nanosecond `select_freshest_venue_quote` (expiring prior-session `BOATS` at `04:00 ET`), `PITSecurityMaster` (`CIK <-> Composite FIGI <-> Ticker` interval map), and `PaperPositionGuardianFSM` fuzzed by `Hypothesis` `RuleBasedStateMachine` (`GuardianLifecycleMachine`).

## Alternatives Considered

1. **Leave `codex-astra-audit`'s 20 harness cases marked `@pytest.mark.xfail`:** Rejected — every defect had a clean, exact mathematical fix (`Decimal` grid + finiteness + dual date bounds).
2. **Enable `2026-12-06` `23/5` SIP session windows unconditionally by date constant:** Rejected because exchange cutover dates can slip; keeping `enable_dec6_235_sip=False` by default prevents silent session drift until go-live is verified.

## Verification Witness

- `mise exec -- uv run pytest -v` executes 100+ unit, adversarial, upstream-parity, and stateful Hypothesis `RuleBasedStateMachine` tests with `0` harness `xfail`s.
- `mise exec -- uv run python scripts/runtime_fleet.py` verifies all `27` multi-model, security, and ingestion CLI binaries (`PASS`).
- `mise exec -- uv run python scripts/architecture_catalog.py --check` verifies `16 ADRs valid, 0 drift`.
