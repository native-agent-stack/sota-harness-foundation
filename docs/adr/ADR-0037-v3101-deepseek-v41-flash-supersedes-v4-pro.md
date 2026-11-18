# ADR-0037: `v3.10.1` Supersede `deepseek-v4-pro` with DeepSeek V4.1 Flash (`deepseek-v4.1-flash` / `deepseek-flash`) in Open-Core Routing & `H6` DSH Lane

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L3 / L4 / L6 / L10 (`P0–P5` × `T1–T5` × `H0–H7`)
- **Evidence Grade:** E4 (`37` ADRs, `https://artificialanalysis.ai/models` & `@deepseek-ai/dsh-agent-default-model` `model: deepseek-flash` Primary-Source Verified, `64/64` Pytest PASS)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/dsh-sota-harness
- **Revisit Trigger:** Artificial Analysis `v5.x` / DeepSeek `v4.x+` release

## Context and Problem Statement

Primary-source verification against [Artificial Analysis](https://artificialanalysis.ai/models) and `dsh --profile headless --dump-default-config` (`@deepseek-ai/dsh-agent-default-model`) confirmed that `deepseek-v4-pro` is superseded by **DeepSeek V4.1 Flash (`deepseek-v4.1-flash`)** (552B MoE, ~8B/16B active parameters per token, `1M`-token context, official API / DSH default slug `deepseek-flash`).

## Decision Outcome

1. **Replace `deepseek-v4-pro` with `deepseek-v4.1-flash` (`alias: "deepseek-flash"`) Across Open-Core Routing & `H6_DEEPSEEK_10LAYER_HARNESS`:**
   - Update `config/multi-model-routing.json`, `scripts/runtime_fleet.py`, `src/cc_sota_harness/workstation_lane.py`, and `UPSTREAM.md` while preserving non-GPT `Hephaestus` (`claude-sonnet-5-5`) and zero-PII open-core invariants.

## Alternatives Considered

- **Keeping `deepseek-v4-pro` in `runtime_fleet.py`:** Rejected — retiring superseded model slugs prevents stale configuration drift across harnesses.

## Verification Witness

- `python3 scripts/architecture_catalog.py && python3 scripts/architecture_catalog.py --check` (`37 ADRs valid, 0 drift`)
- `uv run ruff check . && uv run pytest -q` (`64 passed`) & `gitleaks git --no-banner` (`0` leaks)
