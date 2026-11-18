# ADR-0004: L2 Engineering Method Spine, File Planning & Bounded Autoresearch

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L2` Method Spine & Persistent Planning
- **Evidence Grade:** E2 (Installed & Validated at Exact Git SHAs)
- **Revisit Trigger:** 2027-01-01 or upstream major release

## Context and Problem Statement

Long-running quantitative and execution-engine engineering degrades when plans, falsification checks, and debugging state live solely in conversation memory, or when autonomous iteration loops (`autoresearch`) run without pre-registered bounds.

## Decision Outcome

Adopt four complementary, upstream-installed Claude Code plugins at project scope:

1. **`obra/superpowers` (`v7.0.2` @ `22f0b463e7a5e579904dd6211a520321035526f7`):** Primary TDD, root-cause systematic debugging, git-worktree isolation, and verification-before-completion spine.
2. **`OthmanAdi/planning-with-files` (`v3.28.2` @ `51bf62def62d1cb317d37936929b4ef97cf862c3`):** Manus-style crash-proof Markdown file planning (`task_plan.md`, `findings.md`, `progress.md`) surviving `/compact` and session handoffs.
3. **`EveryInc/compound-engineering-plugin` (`v3.38.1` @ `a3d6a8ee41a404b74391ee278423b52890b8920d`):** Hook-free `Plan -> Work -> Review -> Compound` workflow skills for capturing reusable engineering lessons.
4. **`uditgoenka/autoresearch` (`v2.3.0` @ `7bddd056dfd0b0ded8360588d8101b1ecb5c0baa`):** Bounded `Modify -> Verify -> Keep/Discard` iteration engine, restricted by `CLAUDE.md` and `gates.py` to pre-wall (`<= 2026-10-15`) data and `sota-peer-bus` SHA-256 pre-registration.

## Alternatives Considered

- **`SuperClaude-Org/SuperClaude_Framework` (23.9k★):** Stale relative to native Claude Code `2.1.x` plugin schemas; overlaps `Superpowers` with heavier persona prompts.
- **`frankbria/ralph-claude-code` (9.7k★):** Superseded by native `/ralph` inside `oh-my-claudecode` (`OMC` `v5.8.6`).

## Verification Witness

- `claude plugin list` confirms all four plugins `✔ enabled` (`scope: project`) under both `~/.claude` and Orca's Claude profile.
