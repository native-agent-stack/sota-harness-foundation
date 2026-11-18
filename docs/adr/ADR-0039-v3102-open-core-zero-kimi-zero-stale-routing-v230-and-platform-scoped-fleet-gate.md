# ADR-0039: `v3.10.2` Open-Core Zero-Kimi / Zero-Stale Model Routing (`v2.3.0`) & Platform-Scoped Runtime Fleet Gate

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0 / L1 / L3 / L4 / L8 (`P0–P5` × `T1–T5` × `H0–H7`)
- **Evidence Grade:** E4 (`39` ADRs, `config/multi-model-routing.json` `v2.3.0`, `forbidden_substrings` & Per-OS `platforms` Gate in `scripts/runtime_fleet.py`, `pytest` + Hypothesis + `ruff` + `gitleaks` `0` Leaks)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/cc-sota-harness, https://artificialanalysis.ai/models
- **Revisit Trigger:** Ecosystem `v4.0.0` promotion or `2026-12-06` `23/5` Consolidated SIP cutover

## Context and Problem Statement

1. **Open-Core Parity With `cc-sota-harness` `ADR-0037` / `ADR-0038`:** `sota-harness-foundation` (`PUBLIC` open-core CI foundation) must mirror the `v2.3.0` zero-Kimi / zero-stale multi-model routing matrix (`gemini-4-hydrogen-xhigh`, `deepseek-v4.1-flash`, `claude-sonnet-5-5` non-GPT `Hephaestus`) and truthful per-OS `platforms` metadata (`goose` on `["darwin", "linux"]`, `omniroute` on `["darwin"]`).

## Decision Outcome

1. **Mirror `config/multi-model-routing.json` (`v2.3.0`), `scripts/runtime_fleet.py`, & `src/cc_sota_harness/workstation_lane.py`:**
   - Enforce `forbidden_substrings` (`kimi`, `moonshot`, `deepseek-v4-pro`, `deepseek-v4-flash`, `gemini-3.8-flash`, `gpt-6.1-sol`, `gpt-6-astra`, `claude-fable-5-1`) in `validate_routing_matrix()`, remove `Moonshot AI` / `kimi-k3.1-pro` across `workstation_lane.py` and `UPSTREAM.md`, and honor `platforms` in `runtime_fleet.py`.

## Alternatives Considered

- **Allowing `sota-harness-foundation` routing config to lag `cc-sota-harness`:** Rejected — `H3`/`H5` open-core parity requires identical routing schemas and model-hygiene invariants.

## Verification Witness

- `uv run python scripts/architecture_catalog.py --check` (`39 ADRs valid, 0 drift`)
- `uv run python scripts/runtime_fleet.py --json && uv run pytest -q && mise exec -- ruff check . && mise exec -- gitleaks git --no-banner` (`PASS`, `0` leaks)
