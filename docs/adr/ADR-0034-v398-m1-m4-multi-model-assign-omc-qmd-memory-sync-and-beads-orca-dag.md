# ADR-0034: `v3.9.8` `M1–M4` 1-Call Multi-Model Worker Assignment, `OMC v2` Stop-Callback Contract, `567`-Doc `qmd` 3-Surface Memory Delta Sync & Trial `#96` (`H096`) Governance

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L2 / L3 / L7 / L8 / L10 / L13 (`P0–P5` × `T1–T5` × `H0–H7`)
- **Evidence Grade:** E4 (`34` ADRs, `62/62` Pytest & Hypothesis Property Tests, Live `sota-workstation v2.3.0 coop --sync-memory` Across 3 Surfaces & Pre-Registered Trial `#96` `spec_sha256 = 588d27755bad...`)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/sota-multi-model-workflows, https://github.com/stablyai/orca, https://github.com/tobi/qmd
- **Revisit Trigger:** Ecosystem `v4.0.0` promotion or `2026-12-06` `23/5` Consolidated SIP cutover

## Context and Problem Statement

Following `ADR-0033` (`v3.9.7` `H095` Stage-1 vs Stage-2 collar bifurcation), the open-core `sota-harness-foundation` required public parity with `cc-sota-harness` `ADR-0032` and `sota-multi-model-workflows` `ADR-0020` across cross-workstation recipient normalization, `OMC v2` JSON stop-callback validation, bounded 3-surface E2EE memory delta replication (`lessons`, `handovers`, `hypotheses`), and Trial `#96` (`H096`) governance accounting.

## Decision Outcome

1. **Ship `normalize_coop_recipient()`, `validate_omc_stop_callback_config()`, & `build_memory_delta_sync_plan()` in `src/cc_sota_harness/workstation_lane.py`:**
   - Guarantee cross-workstation peer-bus inbox parity (`mac-m5-agy` / `antigravity` -> `agy`), enforce `claudeMdEnabled=False` alongside per-session JSON `stopHookCallbacks.file` into `omc_stop_callbacks/`, and validate ConPTY-safe temp-file zlib memory replication across `portable_mac_lead`, `stationary_noesis_win32`, and `stationary_noesis_carbon_wsl2` (`>= 567` `qmd` indexed docs).
2. **Codify Pre-Registered Trial `#96` (`H096`) Governance Transition (`v3.9.8`, `N = 96 -> t*(97) = 4.1905`):**
   - Wide `OFI > 0` (`n = 124`, `-12.729 bps` net `1x`, `t = -0.7781 < 4.1882`) is recorded as `FAILED` on `ALPHA_STRATEGY_MINOR`, while strict `OFI >= 0.25 & (ISO_F >= 0.15 | BJZZ >= 0.12)` + `15s` dry-powder bid-survival + `<= 10.0 bps` collar (`n = 52` / `47d`, `+16.835 bps` net `1x` / `+11.366 bps` net `2x`, `11/15 = 73.33%` CPCV `> 0`, `3/3` positive years at `2x`) compounds strictly under `PROTECTIVE_FILTER_OR_GOVERNANCE`.

## Alternatives Considered

- **Leaving `sota-harness-foundation/src/cc_sota_harness/workstation_lane.py` behind private `cc-sota-harness`:** Rejected — violates public open-core architectural symmetry (`zero PII/local paths`).

## Verification Witness

- `uv run python scripts/architecture_catalog.py` & `--check` (`34 ADRs valid, 0 drift`), `uv run ruff check .`, `uv run pytest -q` (`62 passed`), and `gitleaks git --staged --no-banner` (`0` leaks).
