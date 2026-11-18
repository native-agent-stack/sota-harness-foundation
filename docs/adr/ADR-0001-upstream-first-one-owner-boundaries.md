# ADR-0001: Upstream-First, One-Owner-Per-Job & Runtime-Enforced Boundaries

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** Cross-Cutting (`L0–L11` × `T0–T8`)
- **Evidence Grade:** E3 (Runtime-Probed)
- **Revisit Trigger:** 2027-01-01 (45-day cadence) or any change to Claude Code plugin/hook precedence

## Context and Problem Statement

Earlier trading-harness iterations (`edge`, `canon`, ad-hoc scripts in `movers`) either re-implemented orchestration/skills from scratch or relied on prose instructions in `CLAUDE.md` that models can forget after compaction or bypass under `--dangerously-skip-permissions`. At the same time, stacking overlapping agent frameworks without clear ownership causes prompt bloat and hook collisions.

## Decision Outcome

1. **Upstream-First (Bridge, Not Builder):** Every capability across `L0–L11` and `T0–T8` rests on a cited, maintained SOTA upstream pinned by exact version and 40-character Git SHA in `UPSTREAM.md`, `SOTA_ECOSYSTEM_MANIFEST.json`, `mise.lock`, `uv.lock`, `.agents/skills/UPSTREAM_SKILL_PINS.json`, and `~/Documents/upstream/PINS.md`.
2. **One Primary Owner Per Layer:** Each layer assigns a single primary upstream owner (`mise` for L0, `Orca + Claude Code` for L1, `Superpowers + Planning-with-Files` for L2, `OMC` for L3, `Codex Bridge + OMX` for L4, `LSP + Codebase-Memory + CodeGraph + AGY-SOTA-Core` for L5, `Context7 + Financial-Services + K-Dense` for L6, `Context-Mode + Beads + SOTA-Peer-Bus` for L7, `Trail-of-Bits + Cloudflare Security Audit` for L8, `srt + Gitleaks + PreToolUse Guard` for L9, `Claude-HUD + AgentsView` for L10, `18-Repo Shelf + SOTA-Mover-Ranker MCP` for L11).
3. **Runtime-Enforced Safety Below the Model:** All non-negotiable trading, credential, study-wall (`<= 2026-10-15`), and sibling-repo read-only boundaries are enforced deterministically by `.claude/settings.json` (`permissions.deny`), `scripts/trading_harness_guard.py` (`PreToolUse`, fail-closed), `policies/srt-trading-worker.json` (`srt`), and `.githooks/pre-commit` (`gitleaks`).

## Alternatives Considered

- **Custom hand-rolled Python harness only (`movers/tools/harness.py` alone):** Enforces basic tool denials, but forfeits upstream multi-agent orchestration (`OMC`), TDD/debugging spines (`Superpowers`), FTS5 context compression (`Context-Mode`), and dimensional/property verification (`Trail of Bits`).
- **Global unisolated `ECC` (327 skills enabled globally):** Evaluated (`affaan-m/ECC`, 305k★); rejected as a global default due to context-window skill-description bloat and trigger overlap with `Superpowers` and `OMC`.

## Verification Witness

- `mise exec -- uv run python scripts/doctor.py` (`0` errors across all 12 layers & 18 trading upstreams)
- `mise exec -- uv run pytest -v` (verifies fail-closed `PreToolUse` guard from `/` and profile parity)
