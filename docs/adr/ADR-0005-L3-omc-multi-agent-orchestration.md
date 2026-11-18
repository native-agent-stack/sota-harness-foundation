# ADR-0005: L3 Teams-First Multi-Agent Orchestration (`oh-my-claudecode` / `OMC`)

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L3` Multi-Agent Orchestration
- **Evidence Grade:** E3 (Plugin `5.8.6` + CLI `5.8.4` Installed & Probed)
- **Revisit Trigger:** 2027-01-01 or `OMC` major release (`v6.x`)

## Context and Problem Statement

Complex trading-system tasks (simultaneous data-pipeline refactoring, property-test authoring, and cross-model code review) benefit from teams-first multi-agent orchestration (`autopilot`, `ralplan`, `ralph`, `team`, `ultragoal`, `architect`, `blast-radius`), provided OMC does not overwrite global `~/.claude/CLAUDE.md` or leak unattended hooks into live `paper-hand` sessions.

## Decision Outcome

1. **Dual-Surface Upstream Install (`Yeachan-Heo/oh-my-claudecode`, MIT):**
   - **Claude Code Plugin:** `oh-my-claudecode@omc` `v5.8.6` (`dec7e4188c0e3de6b92fb3d734ee5c95326021ed`), enabled at `--scope project` in `.claude/settings.json` (84 skills, 19 agents, `t` bridge MCP server).
   - **Terminal CLI:** `"npm:oh-my-claude-sisyphus" = "5.8.4"` (`sha512-6J2v4Yom...`) locked in `mise.toml` / `mise.lock` (`omc --version` -> `5.8.4`).
2. **Project-Scoped Configuration (`.claude/omc.jsonc`):** Declares stage workflows (`plan-build-qa`, `plan-build-ralph-qa`) and sets `OMC_GIT_GUARDRAILS=1` in `.claude/settings.json` so destructive git actions are blocked in unattended modes. Note per upstream `docs/REFERENCE.md`: named `--workflow` stage profiles require Linux `flock`, while standard `/autopilot`, `/ralph`, `/ralplan`, and `/team` run natively on macOS.
3. **Low-Token Escape Hatch:** `profiles/lean-quant.json` allows launching sessions with `oh-my-claudecode@omc: false` when minimal prompt overhead is desired for tight inner-loop math.

## Alternatives Considered

- **`ruvnet/ruflo` (81.9k★):** Modifies global `CLAUDE.md` and settings aggressively in full mode; rejected per `northstar` ADR-0005 findings.
- **`Chachamaru127/claude-code-harness` (3.2k★):** Smaller single-workflow harness superseded by `OMC` + `Superpowers`.

## Verification Witness

- `mise exec -- omc --version` prints `5.8.4`; `claude plugin list` confirms `oh-my-claudecode@omc` `5.8.6` `✔ enabled`.
