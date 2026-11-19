# ADR-0043: `v3.10.8` Red-Team BugHunter & 4-Tier SkillEvaluator Contract

- **Status:** Accepted
- **Date:** 2026-11-19
- **Layer:** L0 / L2 / L4 / L6 / L7 / L8 (`H1–H3` Security, Red-Team Bug-Hunting, Skill Quality Gates & Trading Firewall Invariants)
- **Evidence Grade:** E4 (`src/cc_sota_harness/redteam_and_skill_eval.py`, `tests/test_redteam_and_skill_eval.py`, `43/43` MADR 4.0 ADRs, Hypothesis property invariants, `pytest` + `ruff` + `gitleaks` `0` Leaks)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/elementalsouls/Claude-BugHunter, https://github.com/NVIDIA/SkillEvaluator, https://github.com/cloudflare/security-audit-skill, https://github.com/NVIDIA/OpenShell, https://github.com/morluto/rea
- **Revisit Trigger:** Addition of new canonical runtime targets beyond the `8` active runtimes or updates to `NVIDIA/SkillEvaluator` / `ADR-0022` firewall rules

## Context and Problem Statement

As the `native-agent-stack` ecosystem scaled to `60` canonical cross-runtime skills (`~/.agents/skills/`), `8` active heterogeneous model runtimes (`claude`, `codex`, `antigravity`, `opencode`, `dsh`, `omp`, `pi`, `muse`), and `415+` starred upstream repositories, two structural verification gaps emerged:
1. **Fragmented Skill & Prompt-Hygiene Validation:** Stale or retired model slugs (`deepseek-v4-pro`, `kimi-*`, retired `grok`/`goose`), conflicting host-topology statements, or overlapping trigger descriptions could silently linger in Markdown skill manifests without an automated `4`-tier pre-sync gate.
2. **Unencoded Red-Team & Firewall Audit Contract:** While individual hooks enforced path leases and live-capital command denials, there was no shared Python contract modeling the `24` red-team vulnerability classes (`Claude-BugHunter`, `cloudflare/security-audit-skill`, `OpenShell`, `rea`) alongside `ADR-0022` stop bounds (`0 < stop <= 2.00%`), bitemporal PIT nanosecond monotonicity (`ts_event_ns <= ts_recv_ns <= decision_ns`), and `P0–P3` deterministic findings.

## Decision Outcome

1. **Adopt the Deterministic Red-Team & Trading-Firewall Audit Contract (`run_redteam_firewall_audit` in `src/cc_sota_harness/redteam_and_skill_eval.py`):**
   - Models `24` canonical vulnerability and firewall classes (`REDTEAM_VULNERABILITY_CLASSES`) covering injection, SSRF, auth/IDOR, TOCTOU races, IEEE-754 non-finite values, secret/home-path leaks, unguarded live-capital endpoints, `ADR-0022` stop cap breaches, bitemporal PIT lookahead violations, and stale/retired model drift.
   - Distinguishes explicitly negated/documented firewall rules (`hard-refused`, `forbidden retired`, `supersedes`) from active violations so security docs do not self-fail while unguarded occurrences fail closed (`P0`/`P1`).
2. **Adopt the 4-Tier `NVIDIA/SkillEvaluator`-Inspired Corpus Gate (`evaluate_skill_directory`, `evaluate_skill_corpus`):**
   - **Tier 1 (Schema & Budget):** Non-empty YAML frontmatter `name` + `description`, bounded file size, and non-trivial body.
   - **Tier 2 (Security & Hygiene):** `0` `P0`/`P1` findings across `SKILL.md` and bundled scripts (`0` secrets, `0` home paths, `0` unguarded live-capital endpoints, `0` stale models).
   - **Tier 3 (Cross-Runtime Compatibility):** Clean slug naming and structural parity across all `8` active runtimes (`CANONICAL_ACTIVE_EIGHT_RUNTIMES`).
   - **Tier 4 (Semantic Overlap):** Token-Jaccard similarity audit across frontmatter descriptions flagging trigger collisions above `overlap_threshold`.

## Alternatives Considered

- **Ad-Hoc Regex Checks in Shell Scripts Only:** Rejected — non-reusable across Python workflows, lacks Hypothesis property testing, and cannot enforce bitemporal/stop/Jaccard invariants uniformly.
- **Blocking On Bare String Matches Inside Negated Firewall Docs:** Rejected — produces false positives in security specifications that explicitly list what is forbidden; context-aware negation markers solve this deterministically.

## Verification Witness

- `uv run ruff check . && uv run ruff format --check .` (`0` errors).
- `uv run pytest -q` (full suite including `test_redteam_and_skill_eval.py` + `40`-example Hypothesis property checks PASS).
- `uv run python scripts/architecture_catalog.py && uv run python scripts/architecture_catalog.py --check` (`43` ADRs valid, `0` drift).
- `gitleaks git --staged` (`0` leaks).
