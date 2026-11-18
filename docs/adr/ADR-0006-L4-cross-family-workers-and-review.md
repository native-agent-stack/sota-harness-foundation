# ADR-0006: L4 Cross-Family Adversarial Review & Worker Fleet (`Codex`, `OMX`, `DSH`, `OmniRoute`)

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L4` Cross-Family Adversarial Review & Multi-Runtime Workers
- **Evidence Grade:** E3 (Installed & Binary-Verified)
- **Revisit Trigger:** 2027-01-01 or OpenAI Codex / DSH protocol update

## Context and Problem Statement

Single-model self-review suffers from correlated blind spots on subtle microstructure, look-ahead bias, and order-state-machine bugs (`meridian` & `tsl` cross-family review rule). Claude Code requires zero-friction delegation to OpenAI Codex and DeepSeek Harness (`DSH`) workers inside Orca.

## Decision Outcome

1. **Official Codex Bridge (`openai/codex-plugin-cc` `v1.0.6` @ `db52e28f4d9ded852ab3942cea316258ae4ef346`):** Installed as `codex@openai-codex` over host `codex` `0.167.1` (3 Orca-managed ChatGPT accounts), enabling `/codex:review`, `/codex:adversarial-review`, and `/codex:rescue` directly from Claude Code.
2. **Codex Worker Enhancement (`Yeachan-Heo/oh-my-codex` `v0.22.10`):** Locked in `mise.toml` (`omx --version` -> `oh-my-codex v0.22.10`) for Codex worker tabs in Orca.
3. **Independent Second-Opinion Skill (`trailofbits/skills:second-opinion` `v1.8.3` @ `149d7b21f4067765b82e67029730b42d228ef4b4`):** Structured uncommitted-diff and branch cross-review across Codex and Antigravity.
4. **Host Router & Second-Family Harness:** Preserves host `OmniRoute` `3.8.53` and `deepseek-ai/dsh` `0.2.2-rc.2` (`dsh-tui` `0.20.0`) in `mise` alongside Orca's `orchestration` worker DAGs.

## Alternatives Considered

- **`nyldn/claude-octopus` (4.4k★) / `SeemSeam/claude_codex_bridge` (3.6k★):** Superseded by OpenAI's official `openai/codex-plugin-cc` (`35.1k★`, Apache-2.0) plus Orca's native multi-agent worktree orchestration.

## Verification Witness

- `mise exec -- codex --version`, `mise exec -- omx --version`, and `claude plugin list` (`codex@openai-codex`, `second-opinion@trailofbits`).
