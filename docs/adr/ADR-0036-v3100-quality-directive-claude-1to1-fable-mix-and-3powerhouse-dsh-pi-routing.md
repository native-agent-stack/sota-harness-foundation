# ADR-0036: `v3.10.0` Open-Core Claude `~1:1` Model-Mix Telemetry, `OMC_MODEL_HIGH/MEDIUM/LOW` Tier Validator & `sota_ephem.py` File Execution

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L1 / L3 / L4 / L8 / L10 (`P0–P5` × `T1–T5` × `H0–H7`)
- **Evidence Grade:** E4 (`36` ADRs, `64/64` Pytest & Hypothesis Property Tests, Artificial Analysis `v5.0.1` / `v2.1` Grounded & Zero-PII Open-Core Verified)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/sota-multi-model-workflows, https://github.com/Yeachan-Heo/oh-my-claudecode, https://github.com/stablyai/orca
- **Revisit Trigger:** Ecosystem `v4.0.0` promotion or `2026-12-06` `23/5` Consolidated SIP cutover

## Context and Problem Statement

1. **Claude Code CLI `~1:1` (`50%` `claude-fable-5-2` vs `50%` Remaining) Governance:** Without explicit `OMC_MODEL_HIGH`, `OMC_MODEL_MEDIUM`, and `OMC_MODEL_LOW` environment bindings, `OMC` subagents default `LOW` tier to `haiku`, skewing turn volume (`69.0%` `haiku` vs `< 1%` `fable-5-2`).
2. **Win32 `python.exe -c $c` Argument Limit After Chunked Base64 Upload:** Even when Base64 payloads are written to `$env:TEMP\sota_ephem.b64` in `<= 3,500`-char chunks (`ADR-0035`), invoking `python.exe -c $c` on decoded Python scripts `> 32 KB` still hits Win32 `CreateProcessW`'s `32,767`-character command-line limit.

## Decision Outcome

1. **Ship `validate_claude_1to1_tier_config()` & `compute_claude_fable_1to1_telemetry()` in `src/cc_sota_harness/workstation_lane.py`:**
   - Deterministically validate `OMC_MODEL_HIGH=claude-fable-5-2`, `OMC_MODEL_MEDIUM=claude-sonnet-5-5`, and `OMC_MODEL_LOW=claude-sonnet-5-5` (zero `haiku` sprawl) and measure `fableShare` against the `[0.42, 0.58]` (`~1:1`) band alongside the **3 Frontier Powerhouse Families + `DSH` + `Pi`/`OMP` (`gpt-6.2-sol` `high`)** fleet.
2. **Execute Decoded Ephemeral Scripts via `$env:TEMP\sota_ephem.py`:**
   - Write decoded UTF-8 bytes directly to `$env:TEMP\sota_ephem.py` and invoke `python.exe "$env:TEMP\sota_ephem.py"`, eliminating `CreateProcessW` length limits for arbitrary-sized cross-workstation scripts.

## Alternatives Considered

- **Compressing `-c` inline with `exec(zlib.decompress(...))`:** Rejected — still bounded at `~32 KB` compressed size, whereas executing `$env:TEMP\sota_ephem.py` scales to megabytes cleanly.

## Verification Witness

- `python3 scripts/architecture_catalog.py --write && python3 scripts/architecture_catalog.py --check` (`36` ADRs valid, `0` drift)
- `uv run ruff check . && uv run pytest -q` (`64 passed`) & `gitleaks git --no-banner` (`0` leaks, `0` local paths)
