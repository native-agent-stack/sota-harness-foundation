# ADR-0029: Dual-Machine Orca Trading Lanes (`T1–T5`) × Harness Lanes (`H0–H7`), Live RTH Contention Shield & Pre-Wall Trial `#90` (`H090`)

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0 / L3 / L5 / L7 / Stage 1–5 (`P0–P5` × `T1–T5` × `H0–H7`)
- **Evidence Grade:** E4 (Architecture & Property Gates) / E3 (Pre-Registered Empirical Trial `#90`)
- **Revisit Trigger:** Addition of a 19th active repository in `native-agent-stack`, `2026-12-06` `23/5` SIP cutover, or whole-market `Noesis-Carbon` `56`-thread expansion of `H090`

## Context and Problem Statement

Following Stage-B closure on `Noesis` (`ADR-0028`, `2.85 TB` free on `Z:` NVMe, `* Noesis-Carbon` `Ubuntu 26.04.1` ext4 online, symmetric `ws://100.93.211.101:6770 <-> ws://100.110.115.22:6770` Orca mesh, and `Z:/sota-data/prewall-lake` seeded), two convergence gaps remained:
1. **Live `09:30` ET RTH Broker Contention:** In `workstation_lane.py`, `HEAVY_PREWALL_RESEARCH` only offloaded to `stationary_noesis_heavy` when on battery (`DUAL_MESH_ON_BATTERY`), leaving docked AC `Mac M5 Max` executing `14`-thread DuckDB/Polars sweeps concurrently with live `:8787`, `:8799`, and `:4002` Paper guardians when `active_broker_host == "portable_mac_lead"`. Furthermore, the `18` active repositories lacked an executable `TradingLaneSpec` (`T1–T5`) × `HarnessLaneSpec` (`H0–H7`) × `8`-Framework bijection check.
2. **Pre-Wall Passive-Bid ORB Toxic-Sweep vs. Trail-Choke Trade-Off (`H085`–`H089`):** `H085` achieved `+7.908` bps net `1x` / `+2.374` bps net `2x` (`t = +0.8151`), whereas `H087`–`H089` proved `45`–`180` bps intraday trailing ratchets choke `97.8%` of runners before `15:55` ET (`-15.16` to `-5.70` bps).

## Decision Outcome

1. **Enforce `18`-Repo Dual-Machine Orca `TradingLaneSpec` (`T1–T5`) × `HarnessLaneSpec` (`H0–H7`) × `8`-Framework Topology & RTH Contention Shield (`dual-workstation-lane-manifest.json` `v1.2.0`):**
   - Partition all `18` active `native-agent-stack` repositories bijectively across `5` Trading Lanes (`T1_MERIDIAN_NAUTILUS_QUEUE_SIM`, `T2_PREWALL_CAUSAL_ALPHA_LAB`, `T3A_ALPACA_200RPM_SIP_PAPER`, `T3B_IBKR_4002_NAUTILUS_PAPER`, `T4_T5_COMPOUNDING_GUARDIAN_VAULT`, all enforcing `0 < stop_cap_pct <= 2.0%`) and `8` Harness Lanes (`H0_ORG_GOVERNANCE_CI` through `H7_MULTI_MODEL_WORKFLOWS_WAL_BUS`) across `8` SOTA orchestration frameworks (`stablyai/orca`, `oh-my-claudecode`, `oh-my-codex`, `google-antigravity`, `oh-my-openagent`, `deepseek-harness`, `hcom-and-sota-peer-bus`, `pi-omp-goose-superspec` spanning `7` model vendors).
   - Offload `56`-thread `HEAVY_PREWALL_RESEARCH` onto `stationary_noesis_heavy` (`* Noesis-Carbon` ext4 + `resolve_prewall_lake_root`) whenever `mesh_online` holds **and** either `DUAL_MESH_ON_BATTERY` or `telemetry.active_broker_host == "portable_mac_lead"`, preserving sub-50ms quote/stop latency on `Mac M5 Max`.
2. **Record Pre-Registered Trial `#90` (`H090_TIGHT_SPREAD_HIGH_OFI_PASSIVE_BID_ADR0022_EOD_HOLD`, `spec_sha256 = c16d2a5794ab...`, `<= 2026-10-15`):**
   - Restricting `hftbacktest::RiskAdverseQueueModel` passive L1 bid entries to tight liquid spreads (`0 < entry_spread_bps <= 10.0`, `ADV_20d >= $20M`, `ofi >= 0.25`, informed ISO/`BJZZ` flow, `RegSHO >= 0.45`, no `90`-day `S-3`/`424B*` dilution) and holding to `15:54` ET under a pure fixed `ADR-0022` `2.00%` `ADVERSE_STOP_FIRST` catastrophe stop achieved **`+20.837` bps net `1x`** (`+2.64x` vs. `H085`), **`+15.425` bps net `2x`** (`+6.50x` vs. `H085`), **`+14.890` bps ex-best-day**, **`5/5` (`100%`) positive `skfolio` CPCV paths**, **`75.81%` (`141/186`) `15:54` ET survival**, and monotonic positive subperiods across `2024` (`+17.14` bps), `2025` (`+15.36` bps), and `2026` (`+39.06` bps).
   - Honestly rejected at Stage 2 under the `90`-trial HLZ hurdle (`t = 1.2919 < 4.1735`, `186 < 200` breadth on the `published-orb` subset), establishing `56`-thread `Noesis-Carbon` whole-market universe expansion (`N -> 2,000+` tight-spread ignitions) as the zero-extra-parameter path to `t >= 4.18`.

## Alternatives Considered

1. **Keep `14`-thread `HEAVY_PREWALL_RESEARCH` on docked `Mac M5 Max` while `:8787`/`:8799`/`:4002` are active:** Rejected — contends with live `24/5` and `09:30` ET quote/trail guardians when `64`-core `Noesis-Carbon` is idle on the LAN mesh.
2. **Relax `t*(90) = 4.1735` or `>= 200`-event breadth gate to pass `H090`:** Rejected — violates Harvey–Liu–Zhu (2016) and `ADIA Lab #19` multiple-testing discipline (`Lesson cc5f5cb81f2ce90c`).

## Verification Witness

- `uv run python scripts/architecture_catalog.py --check` (`29 ADRs valid, 0 drift`), `uv run ruff check .`, `uvx ty@0.0.104 check src scripts tests`, `uv run pytest -q`, and `gitleaks detect --no-git --no-banner` (`0` leaks).
