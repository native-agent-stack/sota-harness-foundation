# ADR-0028: Stage-B `Noesis` `Z:` Reset Completion (`2.85 TB` Free), `* Noesis-Carbon` `Ubuntu 26.04.1` ext4 Promotion & `09:30` ET Protection Convergence

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0 / L1 / L3 / L7 / L9 (`P0–P5` × `T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** `Ubuntu` LTS upgrade beyond `26.04.1`, Tailscale mesh IP rotation, or `2026-12-06` `23/5` Consolidated SIP cutover

## Context and Problem Statement

In `ADR-0021`, `ADR-0025`, and `ADR-0027`, Stage B of the stationary `Noesis` (`Threadripper 64c / 128 GB / RTX 4090`, `100.110.115.22`) workstation reset remained gated pending verified cold archival of the legacy `meridian` WSL2 guest and `Z:` data volumes, leaving `config/dual-workstation-lane-manifest.json` (`v1.0.0`) still declaring `"platform": "win32+wsl2(meridian,sextant)"`. Overnight on `2026-11-18`, `Noesis` completed 100% of Stage B while `:8787` (`sota-mover-ranker` `ADR-0013`) and `:8799` (`sota-dynamic-trail-c` `ADR-0011`) finalized their synchronized `09:30` ET `50/50 + Wave-2 + OFI/UCB` live Paper protection surfaces.

## Decision Outcome

We upgrade `config/dual-workstation-lane-manifest.json` to `manifestVersion = "1.1.0"` and seal the post-Stage-B 3-surface topology:

1. **Stage-B `Noesis` `Z:` Reset Sealed (`+871.6 GB` Reclaimed -> `2.85 TB` Free on `Z:` NVMe):**
   - Legacy `meridian` WSL2 (`120.21 GB` -> `E:/WSL-Recovery-Archives/2026-11-18-StageB-Final/meridian-quiesced-final-20261118.tar`, `tar -tf` verified) and `Z:` legacy data VHDXs/directories were archived non-destructively onto `E:` and unregistered, leaving `Z:` in pure SOTA layout (`Z:/WSL/{Noesis-Carbon, images, sextant, swap}`, `Z:/sota-data/`, `Z:/SextantBackups/`, `Z:/meridian-data/handoff-2026-11-17/`) with `sextant` untouched.
2. **Promote `* Noesis-Carbon` (`Ubuntu 26.04.1 LTS` Native ext4 + RTX 4090 CUDA) in `dual-workstation-lane-manifest.json` (`v1.1.0`):**
   - Update `stationary_noesis_heavy.platform` from `"win32+wsl2(meridian,sextant)"` to `"win32+wsl2(Noesis-Carbon,sextant)"` (`18/18` ext4 repos clean, `18/18` upstream shelf pins, `13/13` AGY probes passing in `~350ms` on native ext4, `10/10` DSH probes, `15/15` `sota-cc-hub` runtimes, and `5m`/`15m` Windows Scheduled Keep-Up & Lease-Safe Sync guards).
3. **Single-Writer `09:30` ET Paper Protection Discipline (`singleActiveBrokerHostOnly = true`):**
   - `portable_mac_lead` (`Mac M5 Max`) remains the single active Paper broker writer (`:8787/api/live_ready_0930_goal`, `:8799/api/live-ready-0930`, `:4002`) enforcing `50/50` Core+Runner convexity, Wave-2 re-entry, and `FINE_TUNED_SELECTIVITY` `OFI`/`UCB` arbitration while `Noesis` + `Noesis-Carbon` absorb `56`-thread / RTX 4090 `CPCV` and pre-wall research sweeps.

## Alternatives Considered

1. **Leave `"win32+wsl2(meridian,sextant)"` in `dual-workstation-lane-manifest.json` after unregistering `meridian`:** Rejected — misdirects WSL2 target probes toward an archived/unregistered guest instead of `* Noesis-Carbon`.
2. **Delete legacy `meridian` WSL2 without `tar -tf` verification on `E:`:** Rejected — Stage B required deterministic archive verification prior to unregistering (`Meridian` `PR #11` `@ 490bd544c8`).

## Verification Witness

- `uv run python scripts/architecture_catalog.py --check` (`28 ADRs valid, 0 drift`), `uv run ruff check .`, `uvx ty@0.0.104 check src scripts tests`, `uv run pytest -q`, and `gitleaks detect --no-git --no-banner` (`0` leaks).
- Live 3-surface `sota-workstation sync --repo all` (`local=18 synced`, `noesis=SYNCED 18`) & `sota-workstation coop --inbox` (`Noesis` `212.89ms` RTT, `0` active lease conflicts).
