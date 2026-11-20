#!/usr/bin/env python3
"""Live Dual-Machine Orca Workstation Lane Inspector & Placement CLI (ADR-0020).

Probes macOS AC/battery state, local Orca runtime (Apple M5 Max 18c/64GB), and paired
stationary Noesis Orca runtime (--environment 100.110.115.22, Threadripper 64c/128GB/RTX4090)
to emit deterministic cross-session / cross-runtime placement decisions.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from cc_sota_harness.workstation_lane import (  # noqa: E402
    HostTelemetry,
    WorkloadKind,
    resolve_workstation_placement,
    validate_dual_workstation_manifest,
)


def _orca_bin() -> str | None:
    found = shutil.which("orca")
    if found:
        return found
    candidate = pathlib.Path.home() / ".local" / "bin" / "orca"
    return str(candidate) if candidate.is_file() else None


def _probe_power() -> tuple[bool, float]:
    if sys.platform != "darwin":
        return True, 100.0
    try:
        out = subprocess.check_output(["/usr/bin/pmset", "-g", "batt"], text=True, timeout=4)
        on_ac = "AC Power" in out
        m = re.search(r"(\d{1,3})%", out)
        pct = float(m.group(1)) if m else 0.0
        return on_ac, pct
    except Exception:
        return False, 0.0


def _probe_paired_orca(orca_bin: str, env_name: str) -> tuple[bool, float | None, int]:
    t0 = time.perf_counter()
    res = subprocess.run(
        [orca_bin, "repo", "list", "--environment", env_name, "--json"],
        capture_output=True,
        text=True,
        timeout=6,
        check=False,
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    if res.returncode != 0:
        return False, None, 0
    try:
        parsed = json.loads(res.stdout)
        if not parsed.get("ok"):
            return False, None, 0
        repos = parsed.get("result", {}).get("repos", [])
        return True, elapsed_ms, len(repos)
    except Exception:
        return False, None, 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and route Dual-Machine Orca Workstation Lane.")
    parser.add_argument("--config-only", action="store_true", help="Validate manifest offline (CI mode)")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--workload",
        choices=[w.value for w in WorkloadKind],
        default=WorkloadKind.COMBINATORIAL_GPU_BATCH.value,
        help="Workload class to resolve placement for",
    )
    parser.add_argument("--repo", default="sota-harness-foundation", help="Target native-agent-stack repo name")
    args = parser.parse_args()

    manifest, errors = validate_dual_workstation_manifest()
    if args.config_only:
        if errors:
            for err in errors:
                sys.stderr.write(f"[FAIL] {err}\n")
            return 1
        out = {
            "ok": True,
            "mode": "config-only",
            "workstations": list(manifest.get("workstations", {}).keys()),
            "noesisProvisionedRepoCount": len(
                manifest["workstations"]["stationary_noesis_heavy"]["provisionedOrcaRepos"]
            ),
        }
        print(json.dumps(out, indent=2) if args.json else "[PASS] Dual-Workstation manifest valid (18 Noesis repos)")
        return 0

    on_ac, batt_pct = _probe_power()
    orca = _orca_bin()
    env_name = manifest["workstations"]["stationary_noesis_heavy"]["tailscaleIp"]
    reachable, rtt_ms, remote_repos = _probe_paired_orca(orca, env_name) if orca else (False, None, 0)

    telemetry = HostTelemetry(
        on_ac_power=on_ac,
        battery_pct=batt_pct,
        paired_host_reachable=reachable,
        paired_rtt_ms=rtt_ms,
        active_broker_host="portable_mac_lead",
    )
    remote_id = manifest["workstations"]["stationary_noesis_heavy"]["provisionedOrcaRepos"].get(args.repo)
    decision = resolve_workstation_placement(
        telemetry,
        WorkloadKind(args.workload),
        repo_name=args.repo,
        remote_repo_id=remote_id,
    )

    report = {
        "ok": len(errors) == 0,
        "errors": errors,
        "telemetry": {
            "onAcPower": on_ac,
            "batteryPct": batt_pct,
            "pairedNoesisReachable": reachable,
            "pairedOrcaRttMs": rtt_ms,
            "pairedProvisionedRepos": remote_repos,
        },
        "placement": {
            "topologyMode": decision.topology_mode.value,
            "workload": decision.workload.value,
            "targetHost": decision.target_host,
            "orcaSelector": decision.orca_selector,
            "allocatedThreads": decision.allocated_threads,
            "approved": decision.approved,
            "reason": decision.reason,
            "orcaCommandTemplate": decision.orca_command_template,
        },
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"[{'PASS' if report['ok'] else 'FAIL'}] mode={decision.topology_mode.value} | "
            f"power={'AC' if on_ac else f'BATT({batt_pct:.0f}%)'} | "
            f"noesis={'ONLINE' if reachable else 'OFFLINE'}"
            f"{f' ({rtt_ms}ms, {remote_repos} repos)' if reachable else ''} | "
            f"target={decision.target_host} ({decision.allocated_threads} threads)"
        )
        print(f"  cmd: {decision.orca_command_template}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
