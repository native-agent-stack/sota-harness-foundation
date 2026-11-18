# ADR-0027: `v3.6.0` Universal `14/14` Workflow Research-Convergence, 6 DataFeed APIs, 4 Strategy Templates, 8 Engine Sources & 3-Surface Workstation Parity

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L1 / L3 / L6 / L8 / L9 / L11 (`T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Addition of a 15th canonical workflow, `2026-12-06` `23/5` `SIP` cutover, or Orca runtime protocol upgrade (`> 1.4.261`)

## Context and Problem Statement

Following `ADR-0025` (hardened headless `orca serve` + lease-safe sync) and `ADR-0026` (`cc-lead` + `OMC` v2 central orchestrator), the open-core foundation harness needed unified `workstation_lane.py` parity (`resolve_workstation_repo_dir`, `probe_noesis_orca_with_retry`, `build_noesis_sync_powershell_commands`, `validate_headless_orca_serve_flags`, `filter_lease_safe_sync_repos`) and `v3.6.0` cross-ecosystem alignment with `sota-multi-model-workflows` (`ADR-0013` `@ 9f7c9aa6d3`), `agy-sota-harness` (`ADR-0019` `@ 53d5808bd4`), and `trading-sota` (`ADR-0012` `@ e838c5bb82`).

## Decision Outcome

1. **Universal `14/14` + `5/5` Workflow Research-Convergence (`sota-workflow-research-convergence.v3.6`):**
   - Bind all `14/14` canonical workflows (`sota-multi-model-workflows`) and `5/5` native `Antigravity` workflows (`agy-sota-harness`) to Turn-0 `verify_workflow_research_convergence(...)`, validating the `6` Trading Lane DataFeed APIs (`:8787`, `:8799`, `:4002`), `4` canonical strategy templates + closed-bar Pine v6, `8` trading engine source repositories, `18` `40`-hex upstream pins, `<= 2026-10-15` pre-wall, `<= 2.00%` stop (`ADR-0022`), and `PHILOSOPHY_ONLY` sibling-repo authority.
2. **Unified 3-Surface Dual-Workstation Helpers (`workstation_lane.py` + `sota-workstation v2.1.0`):**
   - Synchronize `src/cc_sota_harness/workstation_lane.py` across `sota-harness-foundation` and `cc-sota-harness` (`ADR-0025`), supporting seamless repo resolution and lease-safe synchronization across **Apple M5 Max (`~/Documents/*`)**, **stationary `Noesis` Windows (`C:/sota-workstation/*`)**, and **clean `Noesis-Carbon` WSL2 (`~/sota-workstation/*`)**.

## Alternatives Considered

1. **Allow `workstation_lane.py` helper divergence between `cc-sota-harness` and `sota-harness-foundation`:** Rejected — unified superset helpers guarantee `sota-workstation` runs identically whether imported from `cc-sota-harness` or `sota-harness-foundation`.

## Verification Witness

- `scripts/architecture_catalog.py --check` (`27 ADRs valid, 0 drift`), `ruff`, `ty`, `gitleaks`, and `pytest` (`PASS`).
