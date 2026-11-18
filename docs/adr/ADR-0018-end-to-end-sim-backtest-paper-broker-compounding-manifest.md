# ADR-0018: End-to-End `Sim -> Backtest -> Paper (Alpaca/IBKR) -> Empirical-Bayes Compounding` Lifecycle Manifest

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** L2 / L3 / L7 / L8 / L11 (`T1–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Promotion of Trial `N >= 83` (`H06`) past Stage 3 into forward Paper shadow or revision of `ADR-0022 <= 2.00%` stop geometry

## Context and Problem Statement

Across our multi-model research and execution repositories (`meridian`, `cc-sota-harness`, `agy-sota-harness`, `sota-mover-ranker`, `sota-dynamic-trail-c`, and `astrolabe`), quantitative hypotheses progress from causal ideation through queue-aware simulation, pre-wall (`<= 2026-10-15`) historical validation, cross-family adversarial red-teaming, autonomous Paper broker execution (`Alpaca Paper` & `IBKR Paper`), and post-trade factor fine-tuning. Without a single executable state-machine validator and canonical JSON manifest, rejected trials (`H04`, `H05`) or under-tested factor tweaks risk bypassing multiple-testing hurdles (`t*(N)`), 2x square-root market impact checks, or `ADR-0022 <= 2.00%` broker stop caps.

## Decision Outcome

We implement `src/cc_sota_harness/compounding_pipeline.py` and `config/strategy-compounding-manifest.json` (`tests/test_compounding_pipeline.py`), enforcing a deterministic 6-stage (`0..5`) compounding promotion pipeline:

1. **Stage 0 — Immutable Pre-Registration (`0_hypothesis_prereg`):**
   - Requires a 64-hex `SHA-256` specification digest on `sota-bus` (`HYPOTHESIS_LEDGER.md`) and computes the exact Harvey-Liu-Zhu dynamic hurdle `hlz_t_hurdle(N) = round(NormalDist().inv_cdf(1 - 0.00135 / N), 4)` (`t*(79) = 4.1437`, `t*(83) = 4.1550`).
2. **Stage 1 — Upstream Simulation & Queue Parity (`1_sim_queue_parity`):**
   - Pins `nautilus_trader@da6b57aefdd62b44f675e434ffcfefca7f4025dd` (`SpreadAnalyzerParity`, `ContingencyType.OTO=2`) and `hftbacktest@5f3ec40b2afb764e0fea112f941ed85523ef4e88` (`RiskAdverseQueueModel` / `LogProbQueueModel2`).
3. **Stage 2 — Pre-Wall Backtest & 2x Impact Stress (`2_prewall_backtest`):**
   - Enforces `calibration_max_date <= 2026-10-15` (`STUDY_WALL`), `>= 200` events across `>= 60` distinct dates, `CombinatorialPurgedCV(6, 2)` (`>= 80%` positive paths), `DSR >= 0.95`, clustered `t >= t*(N)`, and strictly positive net expectancy at both `1x` and `2x` Almgren-Chriss square-root impact.
4. **Stage 3 — Multi-Model Adversarial Falsification (`3_multimodel_falsification`):**
   - Requires independent sign-off from `>= 3` distinct model families (`anthropic` `claude-fable-5-2`, `openai` `gpt-6.2-astra`, `google` `gemini-4-carbon-high`) with `0` open `P0/P1` defects.
5. **Stage 4 — Autonomous Paper Broker Execution (`4_paper_broker_execution`):**
   - Routes strictly post-wall (`>= 2026-10-16`) approved strategies into:
     - **Alpaca Paper (`PA`, `paper-api.alpaca.markets`)**: `<= 200 req/min` (`180` entry cap + `20` protective exit reserve), RTH `OTO` stop `<= 2.00%`, and extended/overnight `awake_limit_guardian_24x5` (`sota-dynamic-trail-c` `:8799`).
     - **IBKR Paper (`DU`, `127.0.0.1:4002`)**: `<= 3,000 msg/min` (`2,700` entry cap + `300` reserve) and `outside_rth_stop_limit` `<= 2.00%` (`astrolabe` / `sota-mover-ranker` `:8787`).
     - Hard-refuses (`PermissionError`) any live broker target, host (`api.alpaca.markets`), prefix (`U1`), or port (`4001`, `7496`).
6. **Stage 5 — Empirical-Bayes Fine-Tuning & Compounding (`5_compounding_finetune`):**
   - Applies Gaussian Empirical-Bayes precision shrinkage (`empirical_bayes_shrink_edge`) pulling noisy small-sample paper observations toward the pre-wall prior, calibrates range-scaled protective stops via `calibrate_protective_trail_pct` (`<= 2.00%` `ROUND_FLOOR`), and requires `LESSONS.md` root-cause persistence (`H05` `45 bps` vs `170.08 bps` range lesson feeding `H06`).

## Alternatives Considered

1. **Tune factor weights directly on recent Paper P&L without Empirical-Bayes prior shrinkage:** Rejected because small-sample paper streaks have high standard error and induce severe regime overfitting without shrinkage toward the `<= 2026-10-15` pre-wall prior.
2. **Omit rejected trials (`H04`, `H05`) from the manifest:** Rejected because multiple-testing integrity (`N = 82 -> 83`) and compounding learning depend on preserving negative trials and their root-cause stop/cost lessons as regression tests.

## Verification Witness

- `mise exec -- uv run pytest tests/test_compounding_pipeline.py -v` passes unit, live-refusal, manifest-integrity, and Hypothesis property checks (`hlz_t_hurdle` monotonicity, Empirical-Bayes convexity, and `ADR-0022 <= 2.00%` stop clamping).
- `scripts/doctor.py` invokes `validate_compounding_manifest()` on every health check (`0` errors).
