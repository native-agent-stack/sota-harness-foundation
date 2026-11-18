"""Dual-Machine Portable + Stationary Orca Workstation Lane Planner & Firewall (ADR-0020).

Coordinates seamless cross-session and cross-runtime execution between:
- ``portable_mac_lead``: Apple M5 Max (18 cores, 64 GB unified memory) portable workstation
  capable of heavy autonomous offline/roaming research AND interactive ``cc-lead`` control.
- ``stationary_noesis_heavy``: Paired AMD Threadripper (64 logical cores, 128 GB RAM,
  RTX 4090 24 GB) stationary Orca server (``--environment 100.110.115.22``) with all 18
  ``native-agent-stack`` repositories provisioned under ``C:/sota-workstation``.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

DEFAULT_WORKSTATION_MANIFEST_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "config" / "dual-workstation-lane-manifest.json"
)
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

PORTABLE_MAC_MAX_THREADS_AC = 14
PORTABLE_MAC_MAX_THREADS_BATTERY = 8
PORTABLE_MAC_MAX_THREADS_LOW_BATTERY = 4
STATIONARY_NOESIS_MAX_THREADS = 56
MAX_DOCKED_RTT_MS = 1500.0
MIN_BATTERY_PCT_HEAVY = 35.0
MIN_BATTERY_PCT_BROKER = 25.0


class WorkstationTopologyMode(StrEnum):
    DUAL_MESH_DOCKED = "dual_mesh_docked"
    DUAL_MESH_ON_BATTERY = "dual_mesh_on_battery"
    PORTABLE_AUTONOMOUS_AC = "portable_autonomous_ac"
    PORTABLE_AUTONOMOUS_BATTERY = "portable_autonomous_battery"
    PORTABLE_LOW_BATTERY_CONSERVATION = "portable_low_battery_conservation"


class WorkloadKind(StrEnum):
    INTERACTIVE_LEAD = "interactive_lead"
    HEAVY_PREWALL_RESEARCH = "heavy_prewall_research"
    COMBINATORIAL_GPU_BATCH = "combinatorial_gpu_batch"
    PAPER_BROKER_24X5 = "paper_broker_24x5"


@dataclass(frozen=True, slots=True)
class HostTelemetry:
    on_ac_power: bool
    battery_pct: float
    paired_host_reachable: bool
    paired_rtt_ms: float | None = None
    active_broker_host: str | None = None


@dataclass(frozen=True, slots=True)
class PlacementDecision:
    topology_mode: WorkstationTopologyMode
    workload: WorkloadKind
    target_host: str
    orca_selector: str
    allocated_threads: int
    keep_caffeinate_awake: bool
    requires_checkpoint_files: bool
    approved: bool
    reason: str
    orca_command_template: str


def classify_topology_mode(telemetry: HostTelemetry) -> WorkstationTopologyMode:
    if isinstance(telemetry.battery_pct, bool) or not math.isfinite(telemetry.battery_pct):
        raise ValueError(f"battery_pct must be finite, got {telemetry.battery_pct!r}")
    if not (0.0 <= telemetry.battery_pct <= 100.0):
        raise ValueError(f"battery_pct must be in [0, 100], got {telemetry.battery_pct}")
    if telemetry.paired_rtt_ms is not None and (
        isinstance(telemetry.paired_rtt_ms, bool)
        or not math.isfinite(telemetry.paired_rtt_ms)
        or telemetry.paired_rtt_ms < 0.0
    ):
        raise ValueError(f"paired_rtt_ms must be non-negative finite or None, got {telemetry.paired_rtt_ms!r}")

    mesh_fast = telemetry.paired_host_reachable and (
        telemetry.paired_rtt_ms is None or telemetry.paired_rtt_ms <= MAX_DOCKED_RTT_MS
    )
    if mesh_fast:
        return (
            WorkstationTopologyMode.DUAL_MESH_DOCKED
            if telemetry.on_ac_power
            else WorkstationTopologyMode.DUAL_MESH_ON_BATTERY
        )
    if telemetry.on_ac_power:
        return WorkstationTopologyMode.PORTABLE_AUTONOMOUS_AC
    if telemetry.battery_pct >= MIN_BATTERY_PCT_HEAVY:
        return WorkstationTopologyMode.PORTABLE_AUTONOMOUS_BATTERY
    return WorkstationTopologyMode.PORTABLE_LOW_BATTERY_CONSERVATION


def portable_thread_budget(*, on_ac_power: bool, battery_pct: float) -> int:
    if on_ac_power:
        return PORTABLE_MAC_MAX_THREADS_AC
    if battery_pct >= MIN_BATTERY_PCT_HEAVY:
        return PORTABLE_MAC_MAX_THREADS_BATTERY
    return PORTABLE_MAC_MAX_THREADS_LOW_BATTERY


def resolve_workstation_placement(
    telemetry: HostTelemetry,
    workload: WorkloadKind,
    *,
    repo_name: str = "sota-harness-foundation",
    remote_repo_id: str | None = None,
    candidate_broker_host: str = "portable_mac_lead",
) -> PlacementDecision:
    """Resolve deterministic host placement, thread cap, and Orca command across both machines."""
    mode = classify_topology_mode(telemetry)
    local_threads = portable_thread_budget(on_ac_power=telemetry.on_ac_power, battery_pct=telemetry.battery_pct)
    mesh_online = mode in (
        WorkstationTopologyMode.DUAL_MESH_DOCKED,
        WorkstationTopologyMode.DUAL_MESH_ON_BATTERY,
    )
    repo_sel = f"id:{remote_repo_id}" if remote_repo_id else f"github:native-agent-stack/{repo_name}"

    if workload == WorkloadKind.PAPER_BROKER_24X5:
        if (
            telemetry.active_broker_host is not None
            and telemetry.active_broker_host != candidate_broker_host
        ):
            raise PermissionError(
                f"Dual-machine broker split-brain hard-refused: {telemetry.active_broker_host!r} already holds "
                f"the active 24x5 paper broker lease; {candidate_broker_host!r} may not start a second writer"
            )
        if candidate_broker_host == "portable_mac_lead" and (
            not telemetry.on_ac_power and telemetry.battery_pct < MIN_BATTERY_PCT_BROKER
        ):
            return PlacementDecision(
                topology_mode=mode,
                workload=workload,
                target_host="portable_mac_lead",
                orca_selector="--host local",
                allocated_threads=local_threads,
                keep_caffeinate_awake=False,
                requires_checkpoint_files=True,
                approved=False,
                reason=(
                    f"Battery {telemetry.battery_pct:.1f}% < {MIN_BATTERY_PCT_BROKER:.1f}% on portable host; "
                    "autonomous 24x5 paper broker blocked to prevent disconnect naked-share exposure (Canon Lesson 7)"
                ),
                orca_command_template="",
            )
        return PlacementDecision(
            topology_mode=mode,
            workload=workload,
            target_host=candidate_broker_host,
            orca_selector=(
                "--host local"
                if candidate_broker_host == "portable_mac_lead"
                else "--environment 100.110.115.22"
            ),
            allocated_threads=4,
            keep_caffeinate_awake=True,
            requires_checkpoint_files=True,
            approved=True,
            reason="Single-owner 24x5 paper broker lease verified with awake guardian protection",
            orca_command_template="~/.agents/bin/sota-deadman-check",
        )

    if workload == WorkloadKind.INTERACTIVE_LEAD:
        return PlacementDecision(
            topology_mode=mode,
            workload=workload,
            target_host="portable_mac_lead",
            orca_selector="--host local",
            allocated_threads=local_threads,
            keep_caffeinate_awake=telemetry.on_ac_power,
            requires_checkpoint_files=True,
            approved=True,
            reason="Interactive CC Lead (claude-fable-5-2 xhigh) runs natively on Apple M5 Max portable cockpit",
            orca_command_template="orca worktree create --name <task> --parent-worktree active --agent claude --json",
        )

    if workload == WorkloadKind.COMBINATORIAL_GPU_BATCH:
        if mesh_online:
            return PlacementDecision(
                topology_mode=mode,
                workload=workload,
                target_host="stationary_noesis_heavy",
                orca_selector="--environment 100.110.115.22",
                allocated_threads=STATIONARY_NOESIS_MAX_THREADS,
                keep_caffeinate_awake=False,
                requires_checkpoint_files=True,
                approved=True,
                reason="Offloading 56-thread / RTX 4090 batch to stationary Noesis server (survives Mac lid-close)",
                orca_command_template=(
                    f"orca orchestration worker-start --task <task_id> --on 100.110.115.22 "
                    f"--worktree new-child --repo {repo_sel} --name <name> --agent codex --setup run"
                ),
            )
        if mode == WorkstationTopologyMode.PORTABLE_LOW_BATTERY_CONSERVATION:
            return PlacementDecision(
                topology_mode=mode,
                workload=workload,
                target_host="portable_mac_lead",
                orca_selector="--host local",
                allocated_threads=local_threads,
                keep_caffeinate_awake=False,
                requires_checkpoint_files=True,
                approved=False,
                reason=(
                    f"Noesis unreachable and battery {telemetry.battery_pct:.1f}% < {MIN_BATTERY_PCT_HEAVY:.1f}%; "
                    "deferring uncheckpointed combinatorial batch until AC power or Tailscale mesh reconnect"
                ),
                orca_command_template="",
            )
        return PlacementDecision(
            topology_mode=mode,
            workload=workload,
            target_host="portable_mac_lead",
            orca_selector="--host local",
            allocated_threads=local_threads,
            keep_caffeinate_awake=True,
            requires_checkpoint_files=True,
            approved=True,
            reason="Noesis offline; executing heavy batch locally on Apple M5 Max (64 GB unified memory)",
            orca_command_template="orca orchestration worker-start --spec '<task>' --worktree new-child --agent codex",
        )

    # HEAVY_PREWALL_RESEARCH: prefers 64c stationary Noesis when on battery + mesh, or docked; seamlessly runs on M5 Max when carried!
    if mode == WorkstationTopologyMode.DUAL_MESH_ON_BATTERY:
        return PlacementDecision(
            topology_mode=mode,
            workload=workload,
            target_host="stationary_noesis_heavy",
            orca_selector="--environment 100.110.115.22",
            allocated_threads=STATIONARY_NOESIS_MAX_THREADS,
            keep_caffeinate_awake=False,
            requires_checkpoint_files=True,
            approved=True,
            reason="Portable Mac on battery with live Tailscale mesh: offloading heavy research to 64c Noesis to save battery",
            orca_command_template=(
                f"orca orchestration worker-start --task <task_id> --on 100.110.115.22 "
                f"--worktree new-child --repo {repo_sel} --name <name> --agent codex --setup run"
            ),
        )
    return PlacementDecision(
        topology_mode=mode,
        workload=workload,
        target_host="portable_mac_lead",
        orca_selector="--host local",
        allocated_threads=local_threads,
        keep_caffeinate_awake=telemetry.on_ac_power or telemetry.battery_pct >= MIN_BATTERY_PCT_HEAVY,
        requires_checkpoint_files=True,
        approved=True,
        reason=(
            "Apple M5 Max (18c / 64 GB) portable workstation executing heavy DuckDB/Polars research locally "
            f"({local_threads} threads)"
        ),
        orca_command_template="orca worktree create --name <study> --parent-worktree active --agent antigravity --json",
    )


def validate_dual_workstation_manifest(
    manifest_path: pathlib.Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Validate config/dual-workstation-lane-manifest.json invariants and 18-repo provisioning."""
    path = manifest_path or DEFAULT_WORKSTATION_MANIFEST_PATH
    errors: list[str] = []
    if not path.is_file():
        return {}, [f"Missing dual-workstation manifest: {path}"]

    data = json.loads(path.read_text(encoding="utf-8"))
    proto = data.get("crossMachineProtocol", {})
    if proto.get("singleActiveBrokerHostOnly") is not True:
        errors.append("singleActiveBrokerHostOnly must be True to prevent broker split-brain")

    ws = data.get("workstations", {})
    mac = ws.get("portable_mac_lead", {})
    noesis = ws.get("stationary_noesis_heavy", {})
    if mac.get("cpuCores") != 18 or mac.get("memoryGb") != 64:
        errors.append("portable_mac_lead must match verified Apple M5 Max (18 cores, 64 GB)")
    if not (
        0
        < int(mac.get("maxThreadsLowBattery", 0))
        <= int(mac.get("maxThreadsBattery", 0))
        <= int(mac.get("maxThreadsAc", 0))
        < int(mac.get("cpuCores", 0))
    ):
        errors.append("portable_mac_lead thread budgets must satisfy 0 < low_batt <= batt <= ac < cores")

    if noesis.get("cpuCores") != 64 or noesis.get("memoryGb") != 128:
        errors.append("stationary_noesis_heavy must match verified Threadripper (64 cores, 128 GB)")
    if not _UUID_RE.match(str(noesis.get("orcaEnvironmentId", ""))):
        errors.append("stationary_noesis_heavy missing valid orcaEnvironmentId UUID")
    if not _UUID_RE.match(str(noesis.get("orcaRuntimeId", ""))):
        errors.append("stationary_noesis_heavy missing valid orcaRuntimeId UUID")

    repos = noesis.get("provisionedOrcaRepos", {})
    if len(repos) < 18:
        errors.append(f"Expected >= 18 provisioned Orca repos on stationary_noesis_heavy, found {len(repos)}")
    for r_name, r_uuid in repos.items():
        if not _UUID_RE.match(str(r_uuid)):
            errors.append(f"Invalid Orca repo UUID on stationary_noesis_heavy for {r_name}: {r_uuid!r}")

    return data, errors


_FORBIDDEN_WSL_SHARED_VM_RE = re.compile(
    r"(?:\bwsl(?:\.exe)?\s+--shutdown\b|\bwsl(?:\.exe)?\s+-(?:t|-terminate|-unregister)\s+sextant\b)",
    re.IGNORECASE,
)


def enforce_workstation_wsl_and_gateway_guard(
    command: str = "",
    env: dict[str, str] | None = None,
    *,
    tailscale_serve_gateway_unauthenticated: bool = False,
    stage_b_cutover_authorized: bool = False,
) -> None:
    """Enforce ADR-0021 Stage A/B WSL2 cutover guard, Tailscale gateway auth, and OAuth/gateway separation."""
    if not stage_b_cutover_authorized and _FORBIDDEN_WSL_SHARED_VM_RE.search(command):
        raise PermissionError(
            "ADR-0021 Stage A shared-VM WSL2 guard hard-refused command: never run 'wsl --shutdown' or "
            "terminate/unregister co-resident 'sextant' on Noesis without explicit Stage B owner authorization."
        )
    if tailscale_serve_gateway_unauthenticated:
        raise PermissionError(
            "ADR-0021 gateway guard hard-refused unauthenticated Tailscale Serve proxy to loopback model gateway."
        )
    if env:
        base_url = env.get("ANTHROPIC_BASE_URL", "").strip()
        oauth_tok = env.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
        if base_url and oauth_tok:
            raise PermissionError(
                "ADR-0021 / ADR-0053 OAuth guard hard-refused pairing ANTHROPIC_BASE_URL with CLAUDE_CODE_OAUTH_TOKEN."
            )


def build_orca_coop_sync_plan(
    *,
    remote_env: str = "100.110.115.22",
    repo_name: str = "native-agent-stack",
    remote_repo_id: str = "a1875711-afb6-41c3-9ae2-a9e6e46af082",
    remote_path: str = "C:/sota-workstation/native-agent-stack",
    converged_sha: str = "",
    reference_url: str = "https://github.com/native-agent-stack/native-agent-stack",
) -> dict[str, list[str]]:
    """Build deterministic SOTA Orca cross-machine co-op commands (ADR-0022)."""
    if not _UUID_RE.match(remote_repo_id):
        raise ValueError(f"Invalid remote_repo_id UUID: {remote_repo_id!r}")
    if not reference_url.startswith("https://github.com/native-agent-stack"):
        raise ValueError(f"Co-op reference URL must target native-agent-stack org: {reference_url!r}")
    wt_selector = f"id:{remote_repo_id}::{remote_path}"
    short_sha = converged_sha[:10] if converged_sha else "HEAD"
    comment = f"[SOTA CO-OP READY] {repo_name}@{short_sha} synced Mac M5 Max <-> Noesis 64c/RTX4090"
    return {
        "set_comment": [
            "orca",
            "worktree",
            "set",
            "--environment",
            remote_env,
            "--worktree",
            wt_selector,
            "--comment",
            comment,
            "--json",
        ],
        "add_reference": [
            "orca",
            "reference",
            "add",
            "--environment",
            remote_env,
            "--worktree",
            wt_selector,
            "--url",
            reference_url,
            "--json",
        ],
    }


HEADLESS_ORCA_SERVE_REQUIRED_FLAGS: tuple[str, str] = ("--no-pairing", "--refuse-public")


def validate_headless_orca_serve_flags(argv: list[str] | tuple[str, ...]) -> None:
    """Enforce ADR-0025 hardened headless ``orca serve`` flags over Tailscale."""
    tokens = [str(x).strip() for x in argv]
    missing = [flag for flag in HEADLESS_ORCA_SERVE_REQUIRED_FLAGS if flag not in tokens]
    if missing:
        raise PermissionError(
            f"ADR-0025 headless Orca daemon guard hard-refused missing required flags: {missing}"
        )
    for idx, tok in enumerate(tokens[:-1]):
        if tok == "--host" and tokens[idx + 1] in {"0.0.0.0", "::"}:
            raise PermissionError(
                "ADR-0025 headless Orca daemon guard hard-refused wildcard bind; bind solely to Tailscale or loopback IP."
            )


def filter_lease_safe_sync_repos(
    targets: list[str] | tuple[str, ...],
    *,
    remote_active_leases: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    dirty_repos: set[str] | frozenset[str] = frozenset(),
) -> tuple[list[str], dict[str, str]]:
    """Filter candidate git sync targets so leased or dirty repos are never clobbered (ADR-0025)."""
    leased_map: dict[str, str] = {}
    for item in remote_active_leases:
        repo = str(item.get("repo", "")).strip()
        lease_key = str(item.get("lease_key", "")).strip() or f"{repo}::leased"
        if repo and repo not in leased_map:
            leased_map[repo] = lease_key

    safe: list[str] = []
    skipped: dict[str, str] = {}
    for repo in targets:
        if repo in leased_map:
            skipped[repo] = f"remote_lease:{leased_map[repo]}"
        elif repo in dirty_repos:
            skipped[repo] = "dirty_worktree"
        else:
            safe.append(repo)
    return safe, skipped
