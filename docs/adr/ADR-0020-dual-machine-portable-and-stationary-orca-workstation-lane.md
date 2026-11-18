# ADR-0020: Dual-Machine Portable (`Apple M5 Max 64 GB`) + Stationary (`Noesis Threadripper 64c / 128 GB / RTX 4090`) Orca Workstation Lane

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** L0 / L1 / L3 / L4 / L9 / L11 (`T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Enrollment of a third Orca execution host or change to Tailscale/Orca pairing endpoints

## Context and Problem Statement

Our primary interactive cockpit (`portable_mac_lead`) is an **Apple M5 Max MacBook Pro (`18` CPU cores, `64 GB` unified memory)** carried between docked LAN operation and untethered portable operation while running heavy quantitative and multi-model agent workflows. Simultaneously, our stationary workstation **`noesis`** (**AMD Threadripper `64` logical cores, `128 GB` RAM, NVIDIA GeForce RTX 4090 `24,564 MiB`**, Windows + WSL2 `meridian`/`sextant`, Orca `v1.4.261` over Tailscale `ws://100.110.115.22:6770`) is paired directly with Orca (`environmentId: 8ffe74d7-9975-4765-a669-acf7de57510f`, `runtimeId: 4343bf39-d861-48fb-a7bf-c4a1713ed823`).

Without a deterministic dual-machine workstation lane, carrying the MacBook Pro introduces three failure modes:
1. **Unprovisioned Remote Projects:** `orca orchestration worker-start --on 100.110.115.22` fails unless every `native-agent-stack` repository is cloned and registered on the remote Orca runtime.
2. **Hard Remote Coupling or Thermal/Battery Drain:** Workflows that blindly require the desktop break when roaming offline, while running 60-thread combinatorial sweeps locally on low laptop battery risks mid-run shutdown.
3. **Dual-Host Paper Broker Split-Brain & Lid-Close Exposure (`Canon` Lesson 7):** Running two concurrent autonomous broker writers causes symbol collisions, while running an untethered laptop broker below `25%` battery risks naked shares on sleep/disconnect.

## Decision Outcome

We establish a governed **Dual-Machine Orca Workstation Lane** (`config/dual-workstation-lane-manifest.json`, `src/cc_sota_harness/workstation_lane.py`, `scripts/workstation_lane.py`, and `orca.yaml`):

1. **Full 18-Repository Mirror Provisioned on Stationary `noesis` (`C:/sota-workstation/*`):**
   - Cloned and registered all **18** active `https://github.com/native-agent-stack/*` repositories (`sota-harness-foundation`, `native-agent-stack`, `sota-multi-model-workflows`, `sota-compounding-lab`, `sota-upstream-shelf-lock`, `agy-sota-harness`, `dsh-sota-harness`, `astrolabe`, `cc-sota-harness`, `sota-mover-ranker`, `sota-dynamic-trail-c`, `meridian`, `sota-private-vault`, `trading-sota`, `tsl`, `canon`, `dsh-plugin-landscape`, and `.github`) onto `runtime:8ffe74d7-9975-4765-a669-acf7de57510f` via `orca project setup-clone`.
2. **5-State Power & Mesh Topology Classifier (`resolve_workstation_placement`):**
   - **`dual_mesh_docked` (AC + Tailscale `<= 250 ms`):** Interactive `cc-lead` (`claude-fable-5-2` `xhigh`, `14` threads) on M5 Max; `combinatorial_gpu_batch` offloaded via `orca orchestration worker-start --on 100.110.115.22 --worktree new-child --repo id:<uuid>` (`56` threads + `RTX 4090`, surviving laptop lid-close via `terminal.paired-parking.v1`).
   - **`dual_mesh_on_battery` (Battery + Tailscale `<= 250 ms`):** Automatically offloads both `heavy_prewall_research` and `combinatorial_gpu_batch` to `64`-core `noesis` to preserve Mac battery endurance.
   - **`portable_autonomous_ac` / `portable_autonomous_battery` (`>= 35%` battery, `noesis` offline):** Zero remote dependency — executes heavy DuckDB/Polars/CPCV/Hypothesis workflows locally on Apple M5 Max (`64 GB` RAM) scaled monotonically to `14` threads (AC) or `8` threads (battery).
   - **`portable_low_battery_conservation` (`< 35%` battery, `noesis` offline):** Caps interactive threads to `4` and defers uncheckpointed combinatorial batches until AC power or mesh reconnect.
3. **Single-Owner Broker Split-Brain & Roaming Firewall:**
   - Hard-refuses (`PermissionError`) starting `paper_broker_24x5` if the peer workstation already holds `active_broker_host`, and blocks portable autonomous broker execution on battery `< 25%`.

## Alternatives Considered

1. **Sync SQLite `peer_bus.db` binary files across machines over network shares:** Rejected (`agent-ecosystem` host lesson) because WAL shared-memory locks corrupt over network mounts; each host maintains its own fast local bus while cross-machine supervision flows through Orca (`--on 100.110.115.22`) and durable state travels via Git (`native-agent-stack/*`).
2. **Treat the MacBook Pro as a thin client incapable of heavy offline runs:** Rejected because Apple M5 Max (`18` cores, `64 GB` unified memory) handles full Polars/DuckDB Parquet research autonomously when carried.

## Verification Witness

- `scripts/workstation_lane.py` verifies live `pmset` power telemetry, sub-50ms WebSocket reachability to `100.110.115.22`, and `18/18` provisioned remote repositories (`PASS`).
- `tests/test_workstation_lane.py` verifies Hypothesis properties for thread-budget monotonicity, autonomous portable failover, low-battery conservation, and dual-host broker split-brain `PermissionError`.
