# ADR-0013: Artificial Analysis Frontier Model Routing & CC Lead Configuration

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** L1 / L3 / L4
- **Evidence Grade:** E3
- **Revisit Trigger:** Artificial Analysis Intelligence Index v5.x or Coding Agent Index v2.x top-4 rank inversion, or new Anthropic/OpenAI/Google/DeepSeek/Moonshot frontier release

## Context and Problem Statement

Running every task on a single mid-tier or uncalibrated default model wastes reasoning depth on irreversible architecture/quantitative-falsification gates while burning unnecessary tokens on repetitive implementation loops. Worse, switching `/model` mid-session invalidates Claude Code's prompt cache, and pairing structured multi-file refactoring agents (`Hephaestus`) with GPT-family models breaks tool-calling schemas (`oh-my-claudecode` `docs/agents/model-compatibility.md` Rule #2). Meanwhile, `~/.claude/settings.json` and Orca's Codex profile defaults had drifted behind the live November 2026 frontier (`opus` without `effortLevel: "xhigh"` vs `claude-fable-5-2`, and `gpt-6-astra` vs `gpt-6.2-astra`).

## Decision Outcome

We standardize **CC Lead (`cc-lead`)** and cross-runtime worker routing on `config/multi-model-routing.json`, grounded in **Artificial Analysis (`https://artificialanalysis.ai/models`, Intelligence Index v5.0.1 & Coding Agent Index v2.1: `FrontierCode-AA 2.0` + `Terminal-Bench 4.1`)**:

1. **CC Lead Primary & Advisor Model (`claude-fable-5-2`, `xhigh`, `600K` compact window):**
   - Aligned across `~/.claude/settings.json`, Orca's active Claude profile, and `.claude/settings.json` (`"model": "fable"`, `"advisorModel": "claude-fable-5-2"`, `"effortLevel": "xhigh"`, `"autoCompactWindow": 600000`).
   - Ranked **#1 Overall (~65 AA Intelligence Index)** and **#1 Coding Agent (~58 AA Coding Agent Index)**; owns MADR 4.0 ADRs, `Prometheus`/`Hyperplan`/`Oracle` synthesis, and final merge sign-off.
2. **Cross-Family Worker Defaults (`OMC_*_DEFAULT_MODEL` & Orca Codex Profiles):**
   - `OMC_CODEX_DEFAULT_MODEL="gpt-6.2-astra"` (**#2 Overall ~62 AA Intelligence Index**, `max` effort; upgraded across all 3 entitled Orca Codex profiles alongside `gpt-6.2-sol` ~57 for high-throughput parallel sweeps).
   - `OMC_ANTIGRAVITY_DEFAULT_MODEL="gemini-4-carbon-high"` and `OMC_GEMINI_DEFAULT_MODEL="gemini-4-carbon-high"` (**#3 Overall ~60 AA Intelligence Index**, #1 1M+ long-horizon context synthesis across the 18-clone `~/Documents/upstream/` shelf and SEC filings).
   - `OMC_GROK_DEFAULT_MODEL="grok-4.7"` and `omc ask muse` (`muse-spark-1.3`) for independent 4th/5th-family adversarial challenge.
3. **OMC / OMO Role Compatibility & Token-Cost Levers:**
   - `quant-falsifier` binds to `opus` (`claude-opus-5-5`, Co-#1 Coding Agent ~58); `execution-verifier` and `shelf-synthesizer` bind to `sonnet` (`claude-sonnet-5-5`).
   - `Sisyphus` uses `claude-sonnet-5-5` (premium) or `deepseek-v4-pro` (balanced/budget via `dsh` / `OmniRoute`).
   - `Hephaestus` strictly forbids `gpt-*` models (`hephaestusForbidsGptModels: true`), binding only to `claude-sonnet-5-5` or `kimi-k3.1-pro` (#1 open-weight ~46 AA Intelligence Index).
4. **One Model Per Conversation:**
   - Sessions never switch `/model` mid-conversation; cross-tier escalation uses `advisorModel` or isolated worker delegation (`omc ask`, `omc team`, `/codex:adversarial-review`, `council`, `orca worktree create --agent`).

## Alternatives Considered

1. **Keep `~/.claude/settings.json` on `opus` and Codex on `gpt-6-astra`:** Rejected because both trail `claude-fable-5-2` (`xhigh`) and `gpt-6.2-astra` on Artificial Analysis v5.0.1 & Coding Agent Index v2.1 while already entitled in local caches.
2. **Switch `/model` dynamically inside a single long Claude session:** Rejected because mid-conversation model switching invalidates prompt-cache prefixes and multiplies token cost and latency.
3. **Route `Hephaestus` to `gpt-6.2-astra`:** Rejected due to documented structured-output / tool-call breakage in `oh-my-claudecode` / `oh-my-openagent` compatibility testing.

## Verification Witness

- `mise exec -- uv run python scripts/runtime_fleet.py` verifies `ccLead` (`claude-fable-5-2`, `xhigh`), all 11 cataloged frontier models, 7 task-class routes, and the `Hephaestus` non-GPT invariant.
- `mise exec -- uv run python scripts/doctor.py` and `pytest -v` enforce alignment between `.claude/settings.json`, `.claude/agents/*.md`, and `config/multi-model-routing.json`.
