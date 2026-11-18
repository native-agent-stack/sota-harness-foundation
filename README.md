# `sota-harness-foundation` — Open-Core Multi-Model Routing, Execution Parity & Strategy Compounding Foundation

Open-core mathematical, multi-model routing, and 5-stage strategy promotion foundation for **`https://github.com/native-agent-stack`**, continuously verified on **unlimited free GitHub Actions (`ubuntu-latest` + `macos-latest`)**.

> **Two-Tier Visibility Firewall (`ADR-0017`):** This repository (`PUBLIC`) contains strictly zero-secret, zero-home-path, open-core mathematical gates, pinned OSS execution parity (`nautilus_trader` + `hftbacktest`), multi-model routing matrices (`Artificial Analysis v5.0.1 / v2.1`), 18 MADR 4.0 ADRs, and stateful Hypothesis fuzzing. Proprietary empirical Parquet-lake trials and live broker runtimes remain strictly isolated in `PRIVATE` repositories (`native-agent-stack/cc-sota-harness`, `sota-mover-ranker`, `sota-dynamic-trail-c`, `sota-private-vault`, `sota-strategy-vault`).

## Core Open-Core Modules (`src/cc_sota_harness/`)

- **`gates.py`:** `STUDY_WALL <= 2026-10-15` dual-bound date wall, exact `Decimal` `ADR-0022 <= 2.00%` protective stop ceiling, non-loosening ratcheting stop invariants, and paper-only order intent firewall (`PA` `<= 200 req/min`, `DU` `<= 3,000 msg/min`; live capital hard-refused).
- **`institutional_frontier.py`:** Almgren-Chriss square-root market impact + borrow carry (`almgren_chriss_sqrt_impact_bps`), flag-gated `2026-12-06` `23/5` SIP + nanosecond `BOATS` freshness (`resolve_245_session_window`, `select_freshest_venue_quote`), `PITSecurityMaster` (`CIK <-> FIGI <-> Ticker`), and `PaperPositionGuardianFSM` fuzzed by Hypothesis `RuleBasedStateMachine`.
- **`upstream_execution_parity.py`:** Exact transcriptions of pinned `nautilus_trader@da6b57ae` (`SpreadAnalyzerParity`, `ContingencyType.OTO=2`) and `hftbacktest@5f3ec40` (`RiskAdverseQueueModel`, `ProbQueueModel` + 5 probability kernels, Rust half-away tick rounding).
- **`compounding_pipeline.py`:** Deterministic 6-stage (`0..5`) `Hypothesis Pre-Reg (HLZ t*(N)) -> Sim Queue Parity -> Pre-Wall CPCV/DSR/2x-Impact Backtest -> Multi-Model Falsification -> Paper Broker Execution (Alpaca/IBKR) -> Empirical-Bayes Fine-Tuning` validator (`config/strategy-compounding-manifest.json`).

## Local Verification

```bash
uv sync --locked
uv run python scripts/architecture_catalog.py --check
uv run python scripts/runtime_fleet.py --config-only
uv run ruff check .
uvx ty@0.0.104 check src scripts tests
uv run pytest -v
```
