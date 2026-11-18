# ADR-0003: L1 Orca Cockpit, Active Workspace Fleet & Profile Isolation

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L1` Cockpit & Lead Runtime
- **Evidence Grade:** E3 (Live Orca Launch & SessionStart Witness)
- **Revisit Trigger:** 2027-01-01 or Orca major runtime upgrade

## Context and Problem Statement

`stablyai/orca` (`1.4.255`) is the unified multi-agent cockpit on this Mac, managing Claude Code (`2.1.326`, profile `c0ee3cea-8760-4af4-b9d5-7d390f5bfbbb`), 3 Codex accounts, worktrees, and 5 scheduled trading automations. Previously, Orca's project list still carried 4 superseded/archived workspaces (`~`, `canon`, `trading-sota`, `tsl`), lacked `sota-mover-ranker`, `meridian`, `agy-sota-harness`, and `dsh-sota-harness`, and risked global plugin hook leakage into live `paper-hand`/`standby` sessions. In addition, macOS TCC blocks background `launchd` `bash` jobs (`exit 126: Operation not permitted`) on `~/Documents`, making Orca's TCC-authorized runtime the sanctioned scheduler.

## Decision Outcome

1. **Clean Active Orca Fleet (7 Active Repos, 0 Superseded):**
   - Retain & register only active repositories in Orca: `cc-sota-harness`, `sota-mover-ranker`, `movers`, `claude-trading-skills`, `meridian`, `agy-sota-harness`, and `dsh-sota-harness`.
   - Remove superseded idle registrations (`~`, `canon`, `trading-sota`, `tsl`) from Orca via `orca project setup-delete --setup <id> --force --json` while leaving archival directories untouched where required by provenance rules.
2. **Project-Scoped Plugin Isolation (`--scope project`):** All 34 SOTA Claude Code plugins are enabled in `cc-sota-harness/.claude/settings.json` (with `extraKnownMarketplaces` declared inline) rather than mutating global `enabledPlugins`, guaranteeing zero interference with running `movers` and `claude-trading-skills` schedules.
3. **Global `CLAUDE.md` Immunity:** Both `~/.claude/.omc-config.json` and Orca's Claude profile `.omc-config.json` enforce `{"claudeMdEnabled": false}` so OMC updates never overwrite `~/.claude/CLAUDE.md`.
4. **Tracked `orca.yaml` Worktree Bootstrap:** Every child worktree runs `mise trust && mise install --yes && mise exec -- uv sync --locked` with `setupAgentStartupPolicy: wait-for-setup`.

## Alternatives Considered

- **`tmux`-only (`smtg-ai/claude-squad`) or `cmux` without Orca:** Lacks Orca's native multi-account OAuth isolation, structured/terminal session search, and cron precheck scheduler.
- **macOS `launchd` directly on `~/Documents` scripts:** Fails with TCC `exit 126 Operation not permitted` unless `/bin/bash` is granted Full Disk Access; retired for `com.trading-sota.ranking-daily`.

## Verification Witness

- `orca project list --json` lists only the clean active SOTA fleet.
- `private/harness/guard.jsonl` records `SessionStart` `allow` on Orca terminal launch.
