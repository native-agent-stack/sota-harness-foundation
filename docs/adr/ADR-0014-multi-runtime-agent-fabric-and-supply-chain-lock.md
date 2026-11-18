# ADR-0014: Multi-Runtime Agent Fabric (`OMC`, `OMX`, `OMO`, `Pi`, `OMP`, `Goose`, `DSH`) & Supply-Chain Provenance Lock

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** L0 / L3 / L4 / L8
- **Evidence Grade:** E4
- **Revisit Trigger:** Upstream release of major new multi-model CLI harness, Orca native agent enum expansion, or `aube` / `cosign` provenance update for `omniroute` / `worktrunk`

## Context and Problem Statement

A modern trading-system engineering practice spans multiple complementary agent harnesses across the 404-repo starred ecosystem: Claude Code + `OMC` (`oh-my-claudecode`), Codex + `OMX` (`oh-my-codex`), OpenCode + `OMO` (`oh-my-openagent`), `Pi` + `OMP` (`oh-my-pi`), `Antigravity` (`agy`) + `Gemini CLI`, `Goose`, `DeepSeek Harness` (`dsh` + `dsh-tui`), `Muse`, local gateways (`OmniRoute`, `claude-code-router`), context compressors (`rtk`, `repomix`, `qmd`), multi-model deliberation/research plugins (`council-of-high-intelligence`, `ARIS`), and eval/telemetry tools (`promptfoo`, `codeburn`, `worktrunk`, `llmfit`, `hcom`, `code-review-graph`). Installing these ad hoc via global `npm -g` or unverified curl pipes causes PATH drift across Orca terminals and risks supply-chain trust downgrades.

## Decision Outcome

We install, pin, and verify the **24-binary Multi-Runtime Agent Fabric** and **5 starred cross-model / anti-slop Claude plugins** under strict `mise.lock` + `uv tool` + `installed_plugins.json` provenance:

1. **First-Class Multi-Model Harnesses & Orca Native Agents (`mise.toml` + `~/.config/mise/config.toml`):**
   - **Anthropic Lead:** `claude@2.1.326` + `oh-my-claudecode@omc` (`5.8.6` plugin / `5.8.4` CLI).
   - **OpenAI Worker:** `codex@0.169.0` + `oh-my-codex@0.22.10` (`omx`) + `codex@openai-codex` (`1.0.6`).
   - **OpenCode Graph Fabric:** `aqua:anomalyco/opencode@2.3.0` + `npm:oh-my-openagent@5.1.75` (`OMO`).
   - **Pi & OMP Runtime Pair:** `aqua:earendil-works/pi@1.5.2` + `github:can1357/oh-my-pi@18.22.0` (`omp`).
   - **Google DeepMind Pair:** `agy@1.5.3` + `npm:@google/gemini-cli@0.68.0` (`gemini`).
   - **Open-Weights & Independent Harnesses:** `aqua:aaif-goose/goose@1.59.2` (`goose`), `npm:@deepseek-ai/dsh@0.2.2-rc.2` + `npm:@deepseek-harness-tui/dsh-tui@0.20.1`, and `muse@1.4.15`.
2. **Routers, Context Compression, Evals, Worktrees & Code Graph CLIs:**
   - `npm:@musistudio/claude-code-router@3.1.5` (`ccr`) + host-verified `omniroute@3.8.53` (`~/.local/bin/omniroute`).
   - `aqua:rtk-ai/rtk@1.2.0`, `npm:@tobilu/qmd@2.8.3`, `npm:repomix@1.19.0`, `npm:promptfoo@0.125.1`, `npm:codeburn@0.9.28`, `aqua:max-sixty/worktrunk@0.81.0` (`wt`), `github:AlexsJones/llmfit@1.1.20`, `hcom==0.7.31`, and `code-review-graph==2.4.0`.
3. **Starred Multi-Model Deliberation, Autonomous Research & Anti-Slop Plugins (39 Total Project Plugins across 17 Marketplaces):**
   - `council@council-of-high-intelligence` (`1.2.0` @ `c0858f1a`), `aris@aris` (`9f30e834`), `diagram-design@diagram-design` (`2.6.164` @ `f6db0dec`), `impeccable@impeccable` (`4.9.2` @ `d41d9860`), and `hallmark@hallmark` (`2.0.0` @ `04977e15`).
4. **Zero Supply-Chain Verification Bypasses & Credential Isolation:**
   - During lock verification, `mise` `aube` (`trustPolicy=no-downgrade`) flagged transitive `@pierre/theme@1.1.0` on fresh `npm:omniroute` resolution and `cosign` flagged `worktrunk@0.82.0`'s recovery workflow ref. Rather than weakening `trust_policy_excludes` or disabling `cosign`, we locked `aqua:max-sixty/worktrunk@0.81.0` (100% `cosign`-verified across all platforms) and linked the pre-installed `omniroute@3.8.53` binary cleanly via `~/.local/bin/omniroute`.
   - Heavy server/container agents that touch host GitHub/Copilot tokens (`NousResearch/hermes-agent`, `OpenHands`) remain excluded from host-credential CLI install and must run only inside isolated containers if invoked.

## Alternatives Considered

1. **Bypass `mise` `aube` `trustPolicy=no-downgrade` with `trust_policy_excludes` or `npm.shell_out=true`:** Rejected — violates `trailofbits/supply-chain-risk-auditor` discipline and masks upstream attestation regressions.
2. **Install `OpenHands` (85 Python server deps) and `hermes-agent` directly into host `~/.local/bin`:** Rejected due to dependency bloat and documented host `gh`-token exposure risk outside container isolation.
3. **Install Claude-only tooling without `opencode`/`OMO`, `pi`/`OMP`, `gemini`, `goose`, `ccr`, or `promptfoo`:** Rejected because Orca (`claude`, `codex`, `agy`, `muse`, `opencode`, `pi`, `omp`) and `OMC` (`ask`/`team`) treat cross-runtime diversity as a primary falsification mechanism.

## Verification Witness

- `mise install --yes` locks all 43 `mise.toml` / `~/.config/mise/config.toml` tools in `mise.lock` with `0` trust-policy bypasses.
- `mise exec -- uv run python scripts/runtime_fleet.py` resolves all 24 multi-model runtime binaries (`PASS`).
- `mise exec -- uv run python scripts/architecture_catalog.py --check` verifies all 14 MADR 4.0 ADRs with `0` drift.
