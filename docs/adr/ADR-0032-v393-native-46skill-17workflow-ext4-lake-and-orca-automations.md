# ADR-0032: v3.9.3 Unified 46-Skill Cross-Harness Enactment, 17-Workflow Suite, Native `ext4` Pre-Wall Lake Priority & Dual-Machine Orca Automations

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0–L13 × P0–P5 × T1–T5 × H0–H7 (Open-Core Multi-Runtime Foundation & Dual-Workstation Seal)
- **Evidence Grade:** E4 (`32` ADRs, `46/46` SOTA Skills Across AGY+Claude+Codex+Orca, `17/17` Workflows, Native `Noesis-Carbon` `ext4` Lake Priority & Pytest Verified)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/sota-multi-model-workflows, https://github.com/native-agent-stack/cc-sota-harness, https://github.com/stablyai/orca
- **Revisit Trigger:** `2026-12-06` `23/5` Consolidated SIP cutover or `PostWallCohortLedger` reaching `N >= 250`

## Context and Problem Statement

Enacting all SOTA skills and Research-Convergence contracts seamlessly as native workflows across all `11` runtime workers and Dual-Machine Orca (`Mac M5 Max <-> Stationary Noesis 100.110.115.22`) required (1) converging all `46` canonical SOTA skills across `~/.agents/skills`, Antigravity, Claude Code (`cc-lead`), Codex (`OMX`), and `orca skills installed`, (2) binding `sota-workflow` (`ADR-0018`, `17` workflows, `14` layers, `18`-repo ADR index), and (3) prioritizing `* Noesis-Carbon` native `ext4` (`~/sota-data/prewall-lake`, `>20x` faster I/O) ahead of `/mnt/z/sota-data/prewall-lake` (`9p`) in `resolve_prewall_lake_root()`.

## Decision Outcome

1. **Prioritize Native `ext4` `~/sota-data/prewall-lake` in `resolve_prewall_lake_root()` (`workstation_lane.py`):**
   - When resolving default pre-wall lake paths on `Noesis-Carbon` WSL2, check `h / "sota-data" / "prewall-lake"` before `/mnt/z/sota-data/prewall-lake`.
2. **Bind `sota-harness-foundation` (`v3.9.3`, `32` ADRs) to `sota-native-workflow-enactor.v3.10` (`46` Skills × `17` Workflows × Dual-Machine Orca Automations):**
   - Enforce `1:1` parity with `cc-sota-harness` (`ADR-0030`) and `sota-multi-model-workflows` (`ADR-0018`).

## Alternatives Considered

- **Reading `29,500` Parquet files over WSL2 `/mnt/z` `9p` mount when native `ext4` mirror exists:** Rejected; native `ext4` eliminates cross-OS DrvFS metadata overhead.

## Verification Witness

- `uv run python scripts/architecture_catalog.py` & `--check` (`32 ADRs valid, 0 drift`), `uv run ruff check .`, `uv run pytest -q`, and `gitleaks dir . --no-banner` (`0` leaks).
