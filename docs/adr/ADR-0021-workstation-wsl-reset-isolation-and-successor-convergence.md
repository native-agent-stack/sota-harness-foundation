# ADR-0021: Stationary Workstation Clean WSL2/CUDA Isolation, Gateway Firewall & Meridian Successor Convergence

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0 / L1 / L3 / L8 / L9 / L11 (`T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Completion of Noesis `meridian` WSL2 clean re-import or change to shared WSL2 VM topology

## Context and Problem Statement

On `2026-11-17`, the stationary workstation (`noesis`, `100.110.115.22`, AMD Threadripper `64` logical cores, `128 GB` RAM, NVIDIA RTX 4090 `24 GB`) initiated a clean whole-volume/WSL2 reset and formal handoff (`meridian` `ADR-0055` & `ADR-0056`, PRs `#6`, `#7`, `#8`; `sota-private-vault` PR `#1`; `tsl` `owner-open-paper`). Three operational hazards arise on a dual-substrate Windows + shared-VM WSL2 workstation paired over Tailscale:
1. **Shared WSL2 VM Blast Radius:** `meridian` and co-resident `sextant` share a single WSL2 lightweight utility VM on `noesis`; executing `wsl --shutdown` or touching `sextant` / drive `D:` disrupts external co-resident workloads.
2. **Tailscale Serve Loopback Proxy Exposure (`multi-machine-practice-2026-11-15.md`):** Tailscale Serve forwards tailnet traffic to `127.0.0.1`, which would bypass loopback-only assumptions on an unauthenticated local model gateway (`:20128`).
3. **Subscription OAuth Behind Custom Gateways (`meridian` `ADR-0053`):** Passing `CLAUDE_CODE_OAUTH_TOKEN` alongside a custom `ANTHROPIC_BASE_URL` violates subscription-vs-gateway isolation.

## Decision Outcome

We extend `src/cc_sota_harness/workstation_lane.py` (`enforce_workstation_wsl_and_gateway_guard`) and converge the `native-agent-stack` successor ecosystem:

1. **Shared-VM WSL2 & Co-Resident Distro Guard (`enforce_workstation_wsl_and_gateway_guard`):**
   - Hard-refuses (`PermissionError`) any command invoking `wsl --shutdown`, `wsl --terminate sextant`, `wsl --unregister sextant`, or destructive mutations targeting `sextant` or `D:/`.
   - Keeps all `18` active `native-agent-stack` repositories provisioned and FF-synced on `noesis` Windows Orca (`C:/sota-workstation/*`) with live-shimmed multi-model CLIs (`claude`, `codex`, `omc`, `omx`, `oh-my-openagent`, `gemini`, `mise`, `uv`, `rg`, `gitleaks`, `ast-grep`), ready to mount or clone cleanly into a fresh post-reset WSL2/CUDA (`linux-x86_64` + `/usr/lib/wsl/lib/nvidia-smi`) workspace without legacy daemon drift.
2. **Loopback Model Gateway & Subscription OAuth Firewall (`ADR-0053`):**
   - Hard-refuses (`PermissionError`) proxying an unauthenticated local model gateway over Tailscale Serve (`tailscale_serve_gateway_unauthenticated=True`) and hard-refuses pairing `ANTHROPIC_BASE_URL` with `CLAUDE_CODE_OAUTH_TOKEN`.
3. **Full Ecosystem Handoff Convergence (`native-agent-stack` `v3.2.0`):**
   - Absorbs `meridian` `ADR-0001..0057` (`54` ADRs), `tsl` `ADR-0001..0018` (ungated paper promotion with `live` 100% hard-refused), and `sota-private-vault` `ADR-0001..0007` (digest-only access to redacted owner directives and the pre-wall trial ledger).

## Alternatives Considered

1. **Run `wsl --shutdown` from automated scripts to reclaim memory on `noesis`:** Rejected — terminates co-resident `sextant` inside the shared WSL2 VM; bound memory via systemd `MemoryHigh=88G` / `MemoryMax=92G` instead.
2. **Expose local `:20128` gateway via Tailscale Serve without API-key auth:** Rejected — exposes unauthenticated inference to every node on the tailnet.

## Verification Witness

- `tests/test_workstation_lane.py` verifies `PermissionError` hard-refusals for `wsl --shutdown`, `sextant` unregister/terminate, unauthenticated Tailscale gateway proxying, and `ANTHROPIC_BASE_URL` + `CLAUDE_CODE_OAUTH_TOKEN` pairing (`PASS`).
- `scripts/architecture_catalog.py --check` verifies `21 ADRs valid, 0 drift`.
