# ADR-0044: `v3.10.10` Adversarial Landscape Audit, Tier-3 Cross-Runtime Mount Parity & `ext4` Storage Hardening

- **Status:** Accepted
- **Date:** 2026-11-19
- **Layer:** L0 / L2 / L4 / L6 / L7 / L8 (`H1–H3` Cross-Vendor Red-Team Security, 4-Tier SkillEvaluator Mount Parity, Zero-Stale Model Enforcement & WSL2 `ext4` Parity)
- **Evidence Grade:** E4 (`src/cc_sota_harness/redteam_and_skill_eval.py`, `tests/test_redteam_and_skill_eval.py` `12/12` pytest + Hypothesis, `evaluate_skills.py --check-mounts --json` `60/60` PASS across all `8` runtime mounts with `0` missing / `0` drifted / `0` broken symlinks, `44/44` MADR 4.0 ADRs, `ruff` + `ty` + `gitleaks` `0` Leaks)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/NVIDIA/SkillEvaluator, https://github.com/elementalsouls/Claude-BugHunter, https://github.com/cloudflare/security-audit-skill, https://github.com/NVIDIA/OpenShell
- **Revisit Trigger:** Addition of a 9th active runtime skill mount target, updates to `NVIDIA/SkillEvaluator` evaluation tiers, or addition of retired frontier model slugs beyond the current `FORBIDDEN_STALE_MODEL_SLUGS` registry.

## Context and Problem Statement

An adversarial four-track cross-vendor audit of the `v3.10.10` landscape identified three silent verification gaps in `sota-harness-foundation`'s `ADR-0043` `redteam_and_skill_eval.py` evaluator and storage-tier defaults:

1. **Simulated Tier-3 Cross-Runtime Parity:** `evaluate_skill_directory()` previously verified directory slug naming and assumed compatibility with `CANONICAL_ACTIVE_EIGHT_RUNTIMES` without inspecting bundled Python helper scripts for syntax errors, without catching broken skill symlinks in the canonical corpus, and without verifying SHA-256 content parity across the actual `8` mounted runtime skill directories (`antigravity`, `claude`, `codex`, `dsh`, `muse`, `omp`, `opencode`, `pi`).
2. **Incomplete Stale-Model & Linux Home-Path Coverage:** `FORBIDDEN_STALE_MODEL_SLUGS` omitted recently forbidden retired model slugs (`claude-fable-5-1`, `gpt-6-astra`, `gpt-6.1-sol`, `gemini-3.8-flash`), and `_HOME_PATH_PATTERNS` only checked macOS and Windows home paths while omitting Linux home-directory leaks.
3. **WSL2 `ext4` Storage Tier Truthfulness:** `sota-harness-foundation` runtime probes and storage-tier helpers needed consistent alignment with the `Noesis-Carbon` durable `native_ext4` pre-wall lake and zero-waste `UV_LINK_MODE=hardlink` invariants (`ADR-0036` / `ADR-0047`).

## Decision Outcome

1. **Upgrade `evaluate_skill_directory()` & `evaluate_skill_corpus()` to Real Tier-3 Verification (`src/cc_sota_harness/redteam_and_skill_eval.py`):**
   - Parse every bundled `*.py` script inside each skill directory via Python's `ast.parse()` during Tier-3 validation so broken scripts fail closed before cross-runtime sync.
   - Detect broken symlinks in both the canonical `~/.agents/skills/` corpus and every runtime mount directory.
   - Add an optional `runtime_mount_roots: Mapping[str, Path] | None` parameter to `evaluate_skill_corpus()` (invoked by `evaluate_skills.py --check-mounts`) that hashes the full skill-directory file manifest (`SKILL.md` + executable `scripts/*.py` + resources, excluding `__pycache__`/`.pyc`) with SHA-256 and verifies `0` missing skills, `0` SHA-256 content or script drift, and `0` broken symlinks across all `8` mounted runtimes, folding `mount_parity` and `mounts_checked` into `all_passed` and `report_sha256`.
2. **Expand `FORBIDDEN_STALE_MODEL_SLUGS` & 3-OS Home-Path Firewall:**
   - Reject all forbidden retired frontier slugs (`claude-fable-5-1`, `gpt-6-astra`, `gpt-6.1-sol`, `gemini-3.8-flash`, `deepseek-v4-pro`, `deepseek-v4-flash`, `kimi-*`, `moonshot/*`, Haiku sprawl) and detect concrete macOS, Win32, and Linux home paths uniformly across `run_redteam_firewall_audit()`.
3. **Lock Deterministic Unit + Property Regression Coverage (`tests/test_redteam_and_skill_eval.py`):**
   - Add tests verifying Tier-3 `runtime_mount_roots` pass/drift/missing detection, broken Python script AST rejection, and newly added stale model slug rejection.

## Alternatives Considered

- **Checking Only File Existence (Not SHA-256) Across Runtime Mounts:** Rejected — copied skill mounts on Win32 (where symlinks may materialize as copies) can silently drift after canonical edits; SHA-256 byte verification catches any stale copy deterministically.
- **Running `python -m py_compile` Subprocesses Per Skill Script:** Rejected — `ast.parse()` in-process is deterministic, zero-bytecode-side-effect, and 50x faster across 60 skills.

## Verification Witness

- `uv run ruff check . && uv run ruff format --check . && uv run ty check src/cc_sota_harness/redteam_and_skill_eval.py` (`0` errors).
- `uv run pytest -q` (full suite including `12/12` tests in `tests/test_redteam_and_skill_eval.py` PASS).
- `evaluate_skills.py --check-mounts --json` (`60/60` PASS, `8/8` runtime mounts `ok=true`, `0` missing, `0` drifted, `0` broken symlinks).
- `uv run python scripts/architecture_catalog.py && uv run python scripts/architecture_catalog.py --check` (`44` ADRs valid, `0` drift) & `gitleaks protect --staged --no-banner` (`0` leaks).
