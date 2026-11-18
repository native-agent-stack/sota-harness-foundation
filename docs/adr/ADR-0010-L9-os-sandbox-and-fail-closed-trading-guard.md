# ADR-0010: L9 OS-Level Sandbox Runtime, Secret Firewall & Fail-Closed Trading Guard

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L9` Runtime Containment, Privacy & Trading Safety Firewall
- **Evidence Grade:** E3 (18 Adversarial Payloads Blocked From `/`)
- **Revisit Trigger:** 2027-01-01 or any broker/permission surface change

## Context and Problem Statement

Orca launches autonomous jobs with `--dangerously-skip-permissions`. Under `bypassPermissions`, prose rules in `CLAUDE.md` do not block tool execution — only `permissions.deny`, `PreToolUse` hooks, Git pre-commit hooks, and OS-level `sandbox-exec` (`srt`) enforce hard boundaries below the model.

## Decision Outcome

1. **Three-Ring Runtime Firewall:**
   - **Ring 1 — Claude Code `permissions.deny` (`.claude/settings.json`):** Denies `.env*`, `*.credentials.json`, `~/.ssh/**`, `api.alpaca.markets`, `.claude/bin/live open`, macOS Keychain dumps, `mcp__alpaca-live__*`, and `Edit`/`Write` on all closed sibling repositories.
   - **Ring 2 — Fail-Closed `PreToolUse` Guard (`scripts/trading_harness_guard.py`):** Blocks live Alpaca (`api.alpaca.markets`), live IBKR ports (`4001`, `7496`), `TradingClient(..., paper=False)`, unfiltered `printenv`, Keychain extraction, writing `PA...`/`DU...` or `PK`/`AK`/`sk-` strings into tracked files, mutating git/files in sibling repositories, and subagent (`agent_type`) edits to protected harness files. Any exception or malformed stdin denies the call.
   - **Ring 3 — OS Seatbelt Sandbox (`@anthropic-ai/sandbox-runtime` `0.0.83`):** `policies/srt-trading-worker.json` confines untrusted/worker subprocesses via macOS `sandbox-exec`, denying `api.alpaca.markets`, `~/Library/Keychains`, `~/.ssh`, and sibling repo writes at the kernel boundary.
2. **Staged Commit Firewall (`.gitleaks.toml` + `.githooks/pre-commit`):** `gitleaks` (`8.30.1`) with custom `PA...`/`DU...` and `PK...`/`AK...` rules plus `doctor.py --fast` runs before every commit.

## Alternatives Considered

- **Instruction-only guardrails:** Rejected; models can misparse or drop instructions across compactions.

## Verification Witness

- `tests/test_sota_ecosystem.py::test_guard_fails_closed_and_blocks_violations` (18 adversarial cases run with `cwd="/"`).
