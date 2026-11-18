# ADR-0041: `v3.10.4` Stationary Workstation (`Noesis`) as Primary Always-On `24/5` Host for Main Framework Foundation & Trading Engine; Portable Mac M5 Max as Cockpit & Hot Failover

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0 / L2 / L3 / L6 / L8 / L9 (`T1–T5` × `H0–H7` — Stationary Sovereign Host Topology & Single-Active-Broker-Host Lease)
- **Evidence Grade:** E4 (`41` ADRs, `src/cc_sota_harness/shared_24x5_merit_foundation.py`, `tests/test_shared_24x5_merit_foundation.py`, `pytest` + `ruff` + `gitleaks` `0` Leaks)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/sota-multi-model-workflows, https://github.com/native-agent-stack/sota-dynamic-trail-c, https://github.com/native-agent-stack/sota-mover-ranker, https://github.com/stablyai/orca
- **Revisit Trigger:** `2026-12-06` `23/5` Consolidated SIP cutover or addition of a dedicated cloud colocation host

## Context and Problem Statement

`ADR-0040` established the Shared `24/5` Lossless Foundation (`Paper == Live`), but left the portable MacBook Pro M5 Max (`portable_mac_m5_max`, `100.93.211.101`) designated as the primary always-on trading host. Because a laptop sleeps, closes its lid, switches Wi-Fi networks, and travels, hosting the `24/5` Main Framework Foundation, `4`-account Paper Farm (`:8799`, `:8787`, `:8797`, `:4002`), Stage-5 Live Engine (`:8798`), and IBKR Gateway on a portable machine introduces unavoidable connectivity risk and cross-device IBKR `COMPETE` session collisions with stationary `Noesis`.

## Decision Outcome

1. **Promote Stationary Workstation `Noesis` (`stationary_noesis_win32`, `100.110.115.22`, AMD Threadripper 64c/128GB/RTX4090 + `Noesis-Carbon` WSL2) to `PRIMARY_SOVEREIGN_WORKSTATION_HOST`:**
   - Hosts the always-on `24/5` Main Framework Foundation, `S1`/`S2` Sim lanes, `P1:8799`, `P2:8787`, `P3:8797`, `P4:4002` (IBKR Paper), `L5:8798` (Stage-5 Lossless Live), 4K TradingView Desktop, and scheduled Orca Automations.
2. **Designate Portable MacBook Pro M5 Max (`portable_mac_m5_max`, `100.93.211.101`) as `PORTABLE_COCKPIT_FAILOVER_HOST`:**
   - Acts as the portable interactive command cockpit (read-only mirror of `100.110.115.22` when `Noesis` is active) and explicit hot failover host whenever `Noesis` is offline or undergoing cutover.
3. **Fail-Closed `validate_sovereign_host_authority()`:** Enforces `single_active_broker_host_only = True` in both modes (Noesis Primary OR Mac Failover — never both routing orders simultaneously).

## Alternatives Considered

- **Keeping the portable MacBook Pro as primary `24/5` engine host:** Rejected — laptops cannot guarantee uninterrupted wired `24/5` uptime or eliminate cross-device IBKR/TradingView session collisions.

## Verification Witness

- `uv run python scripts/architecture_catalog.py --write && uv run python scripts/architecture_catalog.py --check` (`41 ADRs valid, 0 drift`).
- `uv run pytest -q && ruff check . && gitleaks detect --source . --no-git --no-banner` (`PASS`, `0` leaks).
