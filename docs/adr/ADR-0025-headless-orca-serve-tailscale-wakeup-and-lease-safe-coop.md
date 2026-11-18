# ADR-0025: Hardened Headless `orca serve`, 1-Packet Tailscale UDP Wakeup & Lease-Safe Dual-Workstation Co-op (`v2.0.0`)

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L1 / L3 / L7 / L9 (`T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Orca runtime protocol upgrade (`> 1.4.261`), Tailscale ACL rotation, or Stage B full-volume cutover completion

## Context and Problem Statement

Following `ADR-0024` (`H088` passive-bid x variance-compressing dynamic trail pre-wall study and `424`-repository research catalog cross-references), live bidirectional co-op execution between the portable Apple M5 Max (`64 GB`) cockpit and the stationary Threadripper / RTX 4090 `Noesis` (`128 GB`, `64` logical cores) server exposed three operational hazards:
1. Cold `orca --environment 100.110.115.22` WebSocket dials could time out when Tailscale's direct LAN UDP tunnel sat `idle`;
2. Windows `ConPTY` terminals wrap output lines at column boundaries (`80`/`120` chars), corrupting line-delimited JSON payloads read back via `orca terminal read`;
3. Unconditional remote `git pull --ff-only` risked disturbing active remote `sota-bus` leases (`sota-mover-ranker::agy-noesis-24x5`) or dirty worktrees.

## Decision Outcome

We standardize `sota-workstation` `v2.0.0` (mirrored on both workstations) and add deterministic runtime guards in `src/cc_sota_harness/workstation_lane.py` (`validate_headless_orca_serve_flags`, `filter_lease_safe_sync_repos`):

1. **Hardened Headless `orca serve` Daemon (`stablyai/orca`):**
   - Stationary headless Orca servers must pass `--no-pairing` and `--refuse-public` bound strictly to the Tailscale or loopback interface (hard-refusing `0.0.0.0` / `::` wildcard binds via `validate_headless_orca_serve_flags`), alongside the clean `Ubuntu 26.04.1` `Noesis-Carbon` WSL2 guest (`agy 1.5.10`, `uv`).
2. **1-Packet Tailscale Idle UDP Wakeup & `ConPTY`-Safe `@@B64:` Co-op Framing:**
   - `_probe_noesis` issues `tailscale ping -c 1 --timeout=1s` before `orca repo list` so idle direct LAN tunnels wake immediately (`~6ms` LAN / `~190ms` full RPC).
   - `sota-workstation coop --inbox` and `--send` frame JSON payloads inside `@@B64:<base64>:END@@`, stripping `ConPTY` row-wrap whitespace prior to Base64 decoding and deduplicating ingested `noesis-agy` messages in the local SQLite WAL `peer_bus.db`.
3. **Remote + Local `sota-bus` Lease-Safe Synchronization & Workflow Mirroring:**
   - `filter_lease_safe_sync_repos` and `sota-workstation sync` inspect both hosts' `peer_bus.db` `active_leases` and `git status --porcelain` before `git pull --ff-only`, skipping any leased or dirty repo while automatically mirroring all `15` canonical workflow files (`sota-multi-model-workflows/workflows/*`) into `.agents/workflows/`.

## Alternatives Considered

1. **Expose headless `orca serve` with pairing enabled or `0.0.0.0` bind:** Rejected — violates zero-trust workstation isolation (`validate_headless_orca_serve_flags`).
2. **Parse raw newline-delimited JSON from `orca terminal read` on Windows `pwsh.exe`:** Rejected — empirically broken by `ConPTY` column wrapping; `@@B64:` Base64 framing is column-width invariant.

## Verification Witness

- `pytest tests/test_workstation_lane.py` (`test_adr_0025_headless_orca_serve_and_lease_safe_sync_guards` `PASS`), `ruff`, `ty`, `scripts/architecture_catalog.py --check` (`25 ADRs valid, 0 drift`), and `gitleaks` (`0` leaks).
- Live `sota-workstation v2.0.0` execution across Mac M5 Max <-> `Noesis`: `coop --inbox` (`ingestedIntoLocalBus=1`), `sync --repo all` (`18/18` `Noesis` repos + `15` workflow files synced, `0` lease clobbers).
