# ADR-0031: v3.9.0 9-Feed `sota-ranking-datafeeds.v3.8` (`DF1–DF9`), Dual-Machine Orca Lane Hubs v2 & `UPSTREAM.md` Full-Landscape Convergence

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0–L13 × P0–P5 × T1–T5 × H0–H7 (Full-Ecosystem Open-Core Foundation Seal)
- **Evidence Grade:** E4 (`31` ADRs, `58+` Pytest & Hypothesis Property Tests, `64`-Thread `Noesis-Carbon` Pre-Wall Lake Verified)
- **Revisit Trigger:** `2026-12-06` `23/5` Consolidated SIP cutover or `PostWallCohortLedger` reaching `N >= 250`

## Context and Problem Statement

Following `ADR-0029` (`T1–T5` × `H0–H7` 18-repo Dual-Machine Orca lane topology and `H090`) and `ADR-0030` (`v3.8.0` Master Architecture), finalizing `v3.9.0` across `sota-harness-foundation`, `cc-sota-harness`, and `sota-multi-model-workflows` (`ADR-0016`) required:
1. Upgrading `T2_PREWALL_CAUSAL_ALPHA_LAB` and `dual-workstation-lane-manifest.json` (`v1.3.0`) from `sota-research-feeds.v2` (`7` feeds) to the canonical **`9`-feed `sota-ranking-datafeeds.v3.8` (`DF1..DF9`)** contract and anchoring the empirically verified `64`-hex SHA-256 (`a253421e873441740d5d4b410d993cfa7345fe34b88ec4ab7f4eecd537b3f234`) of `Z:/sota-data/prewall-lake` (`/mnt/z/sota-data/prewall-lake`);
2. Embedding explicit `sota-orca-lane-hub.v2` folder selectors (`trading-lanes` and `harness-lanes` across both `Mac M5 Max` and `Noesis`) and root `UPSTREAM.md` SOTA framework & 18-pin provenance.

## Decision Outcome

1. **Bind `sota-ranking-datafeeds.v3.8` (`DF1..DF9`) & Empirical Pre-Wall Lake SHA-256 in `workstation_lane.py` and `dual-workstation-lane-manifest.json` (`v1.3.0`):**
   - Align `T2_PREWALL_CAUSAL_ALPHA_LAB` with `DF1..DF9` (`DF4` `XNYS` `RVOL_tod`, `DF6` SEC XBRL public float, `DF7` FINRA `T-1` short volume, `DF8` FINRA Rule 4560 `T+8` settled short interest, `DF9` VIX/Majors + IBKR `:4002` locate) and record `prewallLakeMirror.sha256`.
2. **Embed `orcaLaneHubs` (`sota-orca-lane-hub.v2`), `ComposioHQ/agent-orchestrator` (`AO`), and `UPSTREAM.md`:**
   - Synchronize `T1..T5` × `H0..H7` sub-lanes bijectively with `sota-multi-model-workflows` (`sota-dual-machine-lanes.v2` `T1..T3` × `H1..H3` folder hubs) across `8` SOTA orchestration frameworks, `17` runtime binaries, and `7` model vendors.

## Alternatives Considered

1. **Leave `dual-workstation-lane-manifest.json` on `sota-research-feeds.v2` without `orcaLaneHubs` or pre-wall SHA-256:** Rejected — creates schema drift against `sota-multi-model-workflows` `v3.9.0` (`ADR-0016`).
2. **Omit root `UPSTREAM.md` in `sota-harness-foundation`:** Rejected — violates `17/17` active repository upstream provenance completeness.

## Verification Witness

- `uv run python scripts/architecture_catalog.py` & `--check` (`31 ADRs valid, 0 drift`), `uv run ruff check .`, `uvx ty@0.0.104 check src scripts tests`, `uv run pytest -q`, and `gitleaks detect --no-git --no-banner` (`0` leaks).
