# ADR-0022: Research-Converged Upstream Contracts & Bidirectional Mac-to-Workstation `agy` Co-op over SOTA Orca

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0–L12 (`T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Addition of a third workstation or revision to Orca federation / `crossStoreLineage` schemas

## Context and Problem Statement

With `native-agent-stack` converged across `22` repositories and `Noesis` (`100.110.115.22:6770`, `64` logical cores, `128 GB` RAM, RTX 4090) running both Orca Desktop (`1.4.261`) and Antigravity (`agy`) alongside the portable Apple M5 Max (`64 GB` RAM, Orca `1.4.255`), two final capabilities are required:
1. **Cross-Repo Research Contract Traceability:** Bind every promotion and pre-wall evaluation rule to the primary upstream commits established in `Canon` (`0169..0176`), `sota-upstream-shelf-lock` (`ADR-0004`), `sota-compounding-lab` (`ADR-0006`), and `Meridian` (`#224` `424`-row starred/evaluated manifest), while preserving the `<= 2.00%` atomic protective stop cap.
2. **Bidirectional `Mac agy <-> Workstation agy` Co-op without Networked SQLite WAL:** Enable both Antigravity hosts to exchange peer handovers, inbox messages, Orca sidebar worktree comments, and GitHub issue/commit references over Orca's authenticated E2EE channel, plus provide a deterministic post-reset WSL2/CUDA bootstrap (`deploy/wsl/bootstrap_clean_sota_wsl.sh`).

## Decision Outcome

1. **Research-Converged Upstream Matrix:**
   - **Dataset Snapshot Digest (`Canon 0170`):** `RFC-8493` BagIt manifests + `https://github.com/golang/mod` (`v0.43.0` `d4f320b92664` `sumdb/dirhash`) `h1:<base64(sha256)>`.
   - **Pre-Registration Power & Passive Queue Gate (`sota-upstream-shelf-lock ADR-0004` × `Canon 0175`):** `https://github.com/ml4t/diagnostic` (`19e76072` ADIA Lab `#19` `MinTRL`/`MDE`, `distinct_dates >= 60`) + `https://github.com/nkaz001/hftbacktest` (`5f3ec40b` `RiskAdverseQueueModel`) + `https://github.com/skfolio/skfolio` (`CombinatorialPurgedCV`).
   - **RVOL, PIT Delisted Eligibility & Overnight Bounds (`Canon 0171–0174`):** `https://github.com/QuantConnect/Lean` (`e28820c9c846` `RelativeDailyVolume.cs`) cumulative same-time-of-day `RVOL`, `https://github.com/massive-com/client-python` (`v2.10.0` `8c2bd1d8d14d`) counts-only PIT delisted-ticker verification + `alpaca-py` `StockBarsRequest.asof`, `<= 8`-symbol/`<= 8h` isolated `BOATS` bounds pre-`2026-12-06` `23/5` SIP, and `<= 2.00%` protective stop cap.
2. **SOTA Orca Co-op Protocol (`build_orca_coop_sync_plan` & `sota-workstation coop`):**
   - Provision `~/.agents/bus/sota_bus_engine.py`, `~/.agents/bin/sota-bus`, `~/.agents/bin/sota-workstation`, `~/.agents/workflows/*`, and `agy`/`antigravity` CLI forwarders on `Noesis`.
   - Exchange `agy <-> agy` messages and `HANDOVER.md` checkpoints over E2EE Orca (`sota-workstation coop send|inbox|sync`) into each host's local `peer_bus.db` (zero networked SQLite WAL locks), while stamping Orca sidebar metadata via `orca worktree set --comment` and `orca reference add`.
3. **Clean Post-Reset WSL2/CUDA Bootstrap (`deploy/wsl/bootstrap_clean_sota_wsl.sh`):**
   - Configures loopback-only `orca-serve` (`127.0.0.1:6790 --refuse-public`), `inotify=1024`, `/usr/lib/wsl/lib/nvidia-smi` verification, and clones/mounts `native-agent-stack` repos without touching co-resident `sextant`, `D:`, or `wsl --shutdown`.

## Alternatives Considered

1. **Mount a single `peer_bus.db` over SMB/Tailscale Drive between Mac and Noesis:** Rejected — corrupts SQLite WAL shared-memory (`-shm`) state across hosts.

## Verification Witness

- `tests/test_workstation_lane.py` verifies `build_orca_coop_sync_plan` (`orca worktree set --comment`, `orca reference add`, and `crossStoreLineage` commands) + `ADR-0021` guards (`PASS`).
- `scripts/architecture_catalog.py --check` verifies `22 ADRs valid, 0 drift`.
