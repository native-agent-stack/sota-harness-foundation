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
import subprocess
import time
from collections.abc import Sequence
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
        if telemetry.active_broker_host is not None and telemetry.active_broker_host != candidate_broker_host:
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
                "--host local" if candidate_broker_host == "portable_mac_lead" else "--environment 100.110.115.22"
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

    # HEAVY_PREWALL_RESEARCH: offloads to 64c stationary Noesis when on battery + mesh OR when portable_mac_lead
    # holds the live 24x5 paper broker lease (:8787/:8799/:4002 sub-50ms jitter shield); runs on M5 Max otherwise.
    if mesh_online and (
        mode == WorkstationTopologyMode.DUAL_MESH_ON_BATTERY or telemetry.active_broker_host == "portable_mac_lead"
    ):
        offload_reason = (
            "Portable Mac holds active 24x5 paper broker lease (:8787/:8799/:4002): offloading 56-thread pre-wall "
            "research to Noesis-Carbon ext4 to preserve sub-50ms quote/stop latency"
            if telemetry.active_broker_host == "portable_mac_lead" and mode == WorkstationTopologyMode.DUAL_MESH_DOCKED
            else "Portable Mac on battery with live Tailscale mesh: offloading heavy research to 64c Noesis to save battery"
        )
        return PlacementDecision(
            topology_mode=mode,
            workload=workload,
            target_host="stationary_noesis_heavy",
            orca_selector="--environment 100.110.115.22",
            allocated_threads=STATIONARY_NOESIS_MAX_THREADS,
            keep_caffeinate_awake=False,
            requires_checkpoint_files=True,
            approved=True,
            reason=offload_reason,
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


def probe_noesis_orca_with_retry(
    orca_bin: str,
    env_name: str = "100.110.115.22",
    *,
    timeout_s: float = 12.0,
    attempts: int = 2,
) -> tuple[bool, float | None, list[dict[str, Any]]]:
    """Probe paired Noesis Orca environment (`timeout=12s`, 1 automatic retry for Tailscale wakeup)."""
    for _attempt in range(max(1, attempts)):
        t0 = time.perf_counter()
        try:
            res = subprocess.run(
                [orca_bin, "repo", "list", "--environment", env_name, "--json"],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        rtt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        if res.returncode != 0:
            continue
        try:
            parsed = json.loads(res.stdout)
            if not parsed.get("ok"):
                continue
            repos = parsed.get("result", {}).get("repos", [])
            return True, rtt_ms, list(repos)
        except (ValueError, TypeError, AttributeError):
            continue
    return False, None, []


def resolve_local_mac_repo_dir(repo_name: str, home: pathlib.Path | None = None) -> pathlib.Path:
    """Resolve canonical local macOS checkout path for any of the 18 provisioned Org repositories."""
    h = home if home is not None else pathlib.Path.home()
    if repo_name == "sota-dynamic-trail-c":
        return h / "sota-dynamic-trail-c"
    if repo_name == "canon":
        return h / "canon"
    if repo_name == ".github":
        dot_gh = h / "Documents" / "dot-github"
        return (
            dot_gh
            if (dot_gh / ".git").exists() or not (h / "Documents" / ".github" / ".git").exists()
            else h / "Documents" / ".github"
        )
    if repo_name == "dsh-plugin-landscape":
        full_name_dir = h / "Documents" / "dsh-plugin-landscape"
        if (full_name_dir / ".git").exists():
            return full_name_dir
        return h / "Documents" / "dsh"
    return h / "Documents" / repo_name


def build_noesis_sync_powershell_commands(
    repos: Sequence[str],
    *,
    skip_leased_repos: Sequence[str] = (),
) -> list[str]:
    """Build PowerShell commands to FF-sync `C:/sota-workstation/*` + `$HOME/.agents/{workflows,skills}` on Noesis."""
    skipped = set(skip_leased_repos)
    ps_cmds: list[str] = []
    for repo in repos:
        if repo in skipped:
            continue
        folder = "dot-github" if repo == ".github" else repo
        ps_cmds.append(f"git -C C:/sota-workstation/{folder} pull --ff-only")
    ps_cmds.append(
        'New-Item -ItemType Directory -Force "$HOME/.agents/workflows" | Out-Null; '
        'Copy-Item -Force C:/sota-workstation/sota-multi-model-workflows/workflows/* "$HOME/.agents/workflows/"'
    )
    ps_cmds.append(
        'New-Item -ItemType Directory -Force "$HOME/.agents/skills" | Out-Null; '
        "if (Test-Path C:/sota-workstation/agy-sota-harness/skills) { "
        'Copy-Item -Recurse -Force C:/sota-workstation/agy-sota-harness/skills/* "$HOME/.agents/skills/" }'
    )
    ps_cmds.append('Write-Output "===SYNC_DONE==="')
    return ps_cmds


HEADLESS_ORCA_SERVE_REQUIRED_FLAGS: tuple[str, str] = ("--no-pairing", "--refuse-public")


def validate_headless_orca_serve_flags(argv: list[str] | tuple[str, ...]) -> None:
    """Enforce hardened headless ``orca serve`` flags over Tailscale."""
    tokens = [str(x).strip() for x in argv]
    missing = [flag for flag in HEADLESS_ORCA_SERVE_REQUIRED_FLAGS if flag not in tokens]
    if missing:
        raise PermissionError(f"Headless Orca daemon guard hard-refused missing required flags: {missing}")
    for idx, tok in enumerate(tokens[:-1]):
        if tok == "--host" and tokens[idx + 1] in {"0.0.0.0", "::"}:
            raise PermissionError(
                "Headless Orca daemon guard hard-refused wildcard bind; bind solely to Tailscale or loopback IP."
            )


def filter_lease_safe_sync_repos(
    targets: list[str] | tuple[str, ...],
    *,
    remote_active_leases: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    dirty_repos: set[str] | frozenset[str] = frozenset(),
) -> tuple[list[str], dict[str, str]]:
    """Filter candidate git sync targets so leased or dirty repos are never clobbered."""
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


def resolve_workstation_repo_dir(
    repo_name: str,
    *,
    home: pathlib.Path | None = None,
    win_root: pathlib.Path | None = None,
) -> pathlib.Path:
    """Resolve an ecosystem repo across Mac (`~/Documents`), Noesis Win32 (`C:/sota-workstation`), and WSL2 (`~/sota-workstation`)."""
    h = home if home is not None else pathlib.Path.home()
    w = win_root if win_root is not None else pathlib.Path("C:/sota-workstation")
    folder = "dot-github" if repo_name == ".github" else repo_name
    candidates: list[pathlib.Path] = []
    if repo_name == "canon":
        candidates.append(h / "canon")
    candidates.extend([h / "Documents" / folder, h / "sota-workstation" / folder, w / folder])
    if repo_name == "dsh-plugin-landscape":
        candidates.insert(1, h / "Documents" / "dsh")
    for cand in candidates:
        if cand.is_dir():
            return cand
    return candidates[0]


def resolve_prewall_lake_root(
    *,
    home: pathlib.Path | None = None,
    wsl_lake: pathlib.Path | None = None,
    win_lake: pathlib.Path | None = None,
) -> pathlib.Path:
    """Resolve canonical `<= 2026-10-15` pre-wall Parquet lake across Mac M5 Max, Noesis Win32, and Noesis-Carbon WSL2."""
    h = home if home is not None else pathlib.Path.home()
    ext4_p = h / "sota-data" / "prewall-lake"
    wsl_p = wsl_lake if wsl_lake is not None else pathlib.Path("/mnt/z/sota-data/prewall-lake")
    win_p = win_lake if win_lake is not None else pathlib.Path("Z:/sota-data/prewall-lake")
    mac_p = h / "Documents" / "market-data"
    ordered = (
        (ext4_p, wsl_p, win_p, mac_p) if (wsl_lake is None and win_lake is None) else (wsl_p, win_p, ext4_p, mac_p)
    )
    for cand in ordered:
        if cand.is_dir():
            return cand
    return mac_p


@dataclass(frozen=True, slots=True)
class TradingLaneSpec:
    lane_id: str
    stage: str
    repos: tuple[str, ...]
    workload_kind: WorkloadKind
    single_writer_paper_only: bool
    endpoint_or_feed: str
    stop_cap_pct: float


@dataclass(frozen=True, slots=True)
class HarnessLaneSpec:
    lane_id: str
    layer: str
    repos: tuple[str, ...]
    primary_framework: str
    lead_model_id: str
    challenger_model_id: str


@dataclass(frozen=True, slots=True)
class OrchestrationFrameworkSpec:
    framework_id: str
    upstream_ref: str
    primary_binary: str
    supported_vendors: tuple[str, ...]
    enforces_one_model_per_session: bool
    forbids_gpt_on_hephaestus: bool


CANONICAL_TRADING_LANES: tuple[TradingLaneSpec, ...] = (
    TradingLaneSpec(
        lane_id="T1_MERIDIAN_NAUTILUS_QUEUE_SIM",
        stage="Stage1_Simulation",
        repos=("meridian",),
        workload_kind=WorkloadKind.COMBINATORIAL_GPU_BATCH,
        single_writer_paper_only=False,
        endpoint_or_feed="NautilusTrader v2.0.0rc9 + hftbacktest::RiskAdverseQueueModel",
        stop_cap_pct=2.0,
    ),
    TradingLaneSpec(
        lane_id="T2_PREWALL_CAUSAL_ALPHA_LAB",
        stage="Stage2_PreWall_Research",
        repos=("canon", "trading-sota", "tsl"),
        workload_kind=WorkloadKind.HEAVY_PREWALL_RESEARCH,
        single_writer_paper_only=False,
        endpoint_or_feed=(
            "sota-ranking-datafeeds.v3.8 (DF1..DF9, <= 2026-10-15, Z:/sota-data/prewall-lake sha256=a253421e8734...)"
        ),
        stop_cap_pct=2.0,
    ),
    TradingLaneSpec(
        lane_id="T3A_ALPACA_200RPM_SIP_PAPER",
        stage="Stage3A_Alpaca_Paper",
        repos=("sota-mover-ranker",),
        workload_kind=WorkloadKind.PAPER_BROKER_24X5,
        single_writer_paper_only=True,
        endpoint_or_feed="http://127.0.0.1:8787 -> paper-api.alpaca.markets (<=200 req/min)",
        stop_cap_pct=2.0,
    ),
    TradingLaneSpec(
        lane_id="T3B_IBKR_4002_NAUTILUS_PAPER",
        stage="Stage3B_IBKR_Paper",
        repos=("astrolabe",),
        workload_kind=WorkloadKind.PAPER_BROKER_24X5,
        single_writer_paper_only=True,
        endpoint_or_feed="127.0.0.1:4002 IBKR Paper L1 (<=3,000 msg/min; 4001/7496 hard-refused)",
        stop_cap_pct=2.0,
    ),
    TradingLaneSpec(
        lane_id="T4_T5_COMPOUNDING_GUARDIAN_VAULT",
        stage="Stage4_5_Compounding_And_Guardian",
        repos=("sota-compounding-lab", "sota-dynamic-trail-c", "sota-private-vault"),
        workload_kind=WorkloadKind.PAPER_BROKER_24X5,
        single_writer_paper_only=True,
        endpoint_or_feed="http://127.0.0.1:8799 [P]/[L]/[M]/[B]/[S] + EB Shrinkage (N>=30 -> N>=250)",
        stop_cap_pct=2.0,
    ),
)

CANONICAL_HARNESS_LANES: tuple[HarnessLaneSpec, ...] = (
    HarnessLaneSpec(
        lane_id="H0_ORG_GOVERNANCE_CI",
        layer="L0",
        repos=(".github",),
        primary_framework="stablyai/orca",
        lead_model_id="claude-fable-5-2",
        challenger_model_id="gpt-6.2-astra",
    ),
    HarnessLaneSpec(
        lane_id="H1_ECOSYSTEM_UMBRELLA_LOCK",
        layer="L1",
        repos=("native-agent-stack",),
        primary_framework="oh-my-claudecode",
        lead_model_id="claude-fable-5-2",
        challenger_model_id="gemini-4-carbon-high",
    ),
    HarnessLaneSpec(
        lane_id="H2_UPSTREAM_40SHA_SHELF_LOCK",
        layer="L2",
        repos=("sota-upstream-shelf-lock",),
        primary_framework="google-antigravity",
        lead_model_id="gemini-4-carbon-high",
        challenger_model_id="claude-opus-5-5",
    ),
    HarnessLaneSpec(
        lane_id="H3_OPEN_CORE_MULTI_RUNTIME_FOUNDATION",
        layer="L3",
        repos=("sota-harness-foundation",),
        primary_framework="oh-my-claudecode",
        lead_model_id="claude-fable-5-2",
        challenger_model_id="gpt-6.2-astra",
    ),
    HarnessLaneSpec(
        lane_id="H4_ANTIGRAVITY_L0_L12_HARNESS",
        layer="L4",
        repos=("agy-sota-harness",),
        primary_framework="google-antigravity",
        lead_model_id="gemini-4-carbon-high",
        challenger_model_id="gpt-6.2-astra",
    ),
    HarnessLaneSpec(
        lane_id="H5_CLAUDE_LEAD_28RUNTIME_HARNESS",
        layer="L5",
        repos=("cc-sota-harness",),
        primary_framework="oh-my-claudecode",
        lead_model_id="claude-fable-5-2",
        challenger_model_id="kimi-k3.1-pro",
    ),
    HarnessLaneSpec(
        lane_id="H6_DEEPSEEK_10LAYER_HARNESS",
        layer="L6",
        repos=("dsh-sota-harness", "dsh-plugin-landscape"),
        primary_framework="deepseek-harness",
        lead_model_id="deepseek-v4-pro",
        challenger_model_id="claude-sonnet-5-5",
    ),
    HarnessLaneSpec(
        lane_id="H7_MULTI_MODEL_WORKFLOWS_WAL_BUS",
        layer="L7",
        repos=("sota-multi-model-workflows",),
        primary_framework="hcom-and-sota-peer-bus",
        lead_model_id="claude-fable-5-2",
        challenger_model_id="gemini-4-carbon-high",
    ),
)

CANONICAL_ORCHESTRATION_FRAMEWORKS: tuple[OrchestrationFrameworkSpec, ...] = (
    OrchestrationFrameworkSpec(
        framework_id="stablyai/orca",
        upstream_ref="https://github.com/stablyai/orca",
        primary_binary="orca",
        supported_vendors=("Anthropic", "OpenAI", "Google DeepMind", "Moonshot AI", "Meta"),
        enforces_one_model_per_session=True,
        forbids_gpt_on_hephaestus=True,
    ),
    OrchestrationFrameworkSpec(
        framework_id="oh-my-claudecode",
        upstream_ref="oh-my-claudecode@omc (Runtime v2)",
        primary_binary="omc",
        supported_vendors=("Anthropic", "OpenAI", "Google DeepMind", "xAI", "Meta"),
        enforces_one_model_per_session=True,
        forbids_gpt_on_hephaestus=True,
    ),
    OrchestrationFrameworkSpec(
        framework_id="oh-my-codex",
        upstream_ref="codex@openai-codex + omx",
        primary_binary="omx",
        supported_vendors=("OpenAI",),
        enforces_one_model_per_session=True,
        forbids_gpt_on_hephaestus=True,
    ),
    OrchestrationFrameworkSpec(
        framework_id="google-antigravity",
        upstream_ref="agy + run_workflow Python DAGs",
        primary_binary="agy",
        supported_vendors=("Google DeepMind", "Anthropic"),
        enforces_one_model_per_session=True,
        forbids_gpt_on_hephaestus=True,
    ),
    OrchestrationFrameworkSpec(
        framework_id="oh-my-openagent",
        upstream_ref="opencode + OMO Hephaestus",
        primary_binary="oh-my-openagent",
        supported_vendors=("Moonshot AI", "Anthropic", "DeepSeek"),
        enforces_one_model_per_session=True,
        forbids_gpt_on_hephaestus=True,
    ),
    OrchestrationFrameworkSpec(
        framework_id="deepseek-harness",
        upstream_ref="dsh + L0-L9 probes",
        primary_binary="dsh",
        supported_vendors=("DeepSeek",),
        enforces_one_model_per_session=True,
        forbids_gpt_on_hephaestus=True,
    ),
    OrchestrationFrameworkSpec(
        framework_id="hcom-and-sota-peer-bus",
        upstream_ref="ComposioHQ/agent-orchestrator + aannoo/hcom + steveyegge/beads + SQLite WAL + @@B64: E2EE",
        primary_binary="hcom",
        supported_vendors=("Anthropic", "OpenAI", "Google DeepMind", "DeepSeek", "Moonshot AI", "xAI", "Meta"),
        enforces_one_model_per_session=True,
        forbids_gpt_on_hephaestus=True,
    ),
    OrchestrationFrameworkSpec(
        framework_id="pi-omp-goose-superspec",
        upstream_ref="pi + omp + goose + github/spec-kit + obra/superpowers",
        primary_binary="pi",
        supported_vendors=("Anthropic", "Moonshot AI", "DeepSeek"),
        enforces_one_model_per_session=True,
        forbids_gpt_on_hephaestus=True,
    ),
)


def resolve_orca_lane_topology(
    telemetry: HostTelemetry,
    *,
    manifest_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Validate 18-repo bijection across T1..T5 & H0..H7 and compute live Dual-Machine Orca placements."""
    manifest, errors = validate_dual_workstation_manifest(manifest_path)
    if errors:
        raise ValueError(f"Invalid dual-workstation manifest: {errors}")

    provisioned: dict[str, str] = manifest["workstations"]["stationary_noesis_heavy"]["provisionedOrcaRepos"]
    trading_repos = [r for lane in CANONICAL_TRADING_LANES for r in lane.repos]
    harness_repos = [r for lane in CANONICAL_HARNESS_LANES for r in lane.repos]
    combined = trading_repos + harness_repos
    if len(combined) != len(set(combined)) or set(combined) != set(provisioned.keys()):
        raise ValueError(
            f"Trading (T1..T5) + Harness (H0..H7) lanes must form an exact 18-repo bijection with provisionedOrcaRepos; "
            f"combined={sorted(combined)}, provisioned={sorted(provisioned.keys())}"
        )

    for lane in CANONICAL_TRADING_LANES:
        if not (0.0 < lane.stop_cap_pct <= 2.0):
            raise ValueError(f"ADR-0022 violation on {lane.lane_id}: stop_cap_pct={lane.stop_cap_pct}")

    distinct_vendors = {v for fw in CANONICAL_ORCHESTRATION_FRAMEWORKS for v in fw.supported_vendors}
    if len(distinct_vendors) < 4:
        raise ValueError(
            f"Expected >= 4 distinct model vendors across orchestration frameworks, got {distinct_vendors}"
        )

    broker_host = telemetry.active_broker_host or "portable_mac_lead"
    trading_placements: dict[str, dict[str, Any]] = {}
    for lane in CANONICAL_TRADING_LANES:
        anchor_repo = lane.repos[0]
        dec = resolve_workstation_placement(
            telemetry,
            lane.workload_kind,
            repo_name=anchor_repo,
            remote_repo_id=provisioned.get(anchor_repo),
            candidate_broker_host=broker_host,
        )
        trading_placements[lane.lane_id] = {
            "stage": lane.stage,
            "repos": list(lane.repos),
            "targetHost": dec.target_host,
            "orcaSelector": dec.orca_selector,
            "allocatedThreads": dec.allocated_threads,
            "approved": dec.approved,
            "singleWriterPaperOnly": lane.single_writer_paper_only,
            "endpointOrFeed": lane.endpoint_or_feed,
        }

    harness_placements: dict[str, dict[str, Any]] = {}
    for h_lane in CANONICAL_HARNESS_LANES:
        anchor_repo = h_lane.repos[0]
        w_kind = (
            WorkloadKind.INTERACTIVE_LEAD
            if h_lane.layer in {"L0", "L1", "L3", "L5", "L7"}
            else WorkloadKind.HEAVY_PREWALL_RESEARCH
        )
        dec = resolve_workstation_placement(
            telemetry,
            w_kind,
            repo_name=anchor_repo,
            remote_repo_id=provisioned.get(anchor_repo),
            candidate_broker_host=broker_host,
        )
        harness_placements[h_lane.lane_id] = {
            "layer": h_lane.layer,
            "repos": list(h_lane.repos),
            "primaryFramework": h_lane.primary_framework,
            "leadModel": h_lane.lead_model_id,
            "challengerModel": h_lane.challenger_model_id,
            "targetHost": dec.target_host,
            "orcaSelector": dec.orca_selector,
            "allocatedThreads": dec.allocated_threads,
        }

    return {
        "manifestVersion": manifest.get("manifestVersion"),
        "topologyMode": str(classify_topology_mode(telemetry)),
        "reposPartitionedTotal": len(combined),
        "distinctVendorsTotal": len(distinct_vendors),
        "frameworksTotal": len(CANONICAL_ORCHESTRATION_FRAMEWORKS),
        "tradingLanes": trading_placements,
        "harnessLanes": harness_placements,
    }


def normalize_coop_recipient(recipient: str, *, direction: str = "inbound_to_mac") -> str:
    """Normalize cross-workstation peer-bus recipients so AGY, CC-Lead, and Lanes receive messages."""
    rcpt = (recipient or "").strip()
    if direction == "inbound_to_mac":
        if not rcpt or rcpt in {"mac-m5-agy", "antigravity"}:
            return "agy"
        return rcpt
    if not rcpt:
        return "*"
    return rcpt


def validate_omc_stop_callback_config(omc_cfg: dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify OMC v2 JSON file stop-hook callback into sota-bus while keeping claudeMdEnabled=False."""
    errs: list[str] = []
    if omc_cfg.get("claudeMdEnabled") is not False:
        errs.append("claudeMdEnabled must remain False to protect lean global CLAUDE.md")
    cb = (omc_cfg.get("stopHookCallbacks") or {}).get("file") or {}
    if cb.get("enabled") is not True:
        errs.append("stopHookCallbacks.file.enabled must be True")
    if cb.get("format") != "json":
        errs.append("stopHookCallbacks.file.format must be 'json'")
    cb_path = str(cb.get("path") or "")
    if "omc_stop_callbacks" not in cb_path or "{session_id}" not in cb_path:
        errs.append("stopHookCallbacks.file.path must write per-session JSON into omc_stop_callbacks/")
    return len(errs) == 0, errs


def build_memory_delta_sync_plan(*, since_hours: float = 2.0, qmd_indexed_docs: int = 567) -> dict[str, Any]:
    """Return bounded 3-surface E2EE memory delta sync contract (Mac M5 Max <-> Noesis Win32 <-> Noesis-Carbon WSL2)."""
    if since_hours <= 0.0 or since_hours > 168.0:
        raise ValueError(f"since_hours must be in (0, 168], got {since_hours}")
    if qmd_indexed_docs < 500:
        raise ValueError(f"Expected >= 500 qmd indexed wiki+ADR docs, got {qmd_indexed_docs}")
    return {
        "schemaVersion": "sota-3surface-memory-sync.v1",
        "sinceHours": round(float(since_hours), 2),
        "tablesSynced": ("lessons", "handovers", "hypotheses"),
        "surfaces": ("portable_mac_lead", "stationary_noesis_win32", "stationary_noesis_carbon_wsl2"),
        "conptyTempFileRelay": True,
        "qmdIndexedDocs": qmd_indexed_docs,
    }


def chunk_powershell_b64_payload(b64_code: str, *, max_chunk_chars: int = 3500) -> list[str]:
    """Split large Base64 payloads into <= max_chunk_chars PowerShell lines below Win32 CreateProcessW 32,767 limit."""
    if max_chunk_chars < 512 or max_chunk_chars > 12000:
        raise ValueError(f"max_chunk_chars must be in [512, 12000], got {max_chunk_chars}")
    if not b64_code:
        return []
    chunks = [b64_code[i : i + max_chunk_chars] for i in range(0, len(b64_code), max_chunk_chars)]
    return [
        f"{'Set-Content' if idx == 0 else 'Add-Content'} -NoNewline -Path \"$env:TEMP\\sota_ephem.b64\" -Value '{ch}'"
        for idx, ch in enumerate(chunks)
    ]


def tokenize_qmd_bm25_query(repo: str, goal: str, *, max_terms: int = 3) -> str:
    """Extract non-stopword whole tokens for qmd BM25 search without mid-word truncation."""
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "into",
        "across",
        "verify",
        "confirm",
        "audit",
        "check",
        "run",
        "read",
        "only",
        "ack",
        "are",
        "live",
        "reply",
        "via",
    }
    words = [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", f"{repo} {goal}") if w.lower() not in stop]
    dedup: list[str] = []
    for w in words:
        if w.lower() not in {x.lower() for x in dedup}:
            dedup.append(w)
    return " ".join(dedup[: max(1, max_terms)])


def validate_claude_1to1_tier_config(env_map: dict[str, str]) -> tuple[bool, list[str]]:
    """Verify OMC HIGH/MEDIUM/LOW tier env enforces ~1:1 claude-fable-5-2 vs sonnet/opus without haiku sprawl."""
    errs: list[str] = []
    if env_map.get("OMC_MODEL_HIGH") != "claude-fable-5-2":
        errs.append("OMC_MODEL_HIGH must be 'claude-fable-5-2'")
    if env_map.get("OMC_MODEL_MEDIUM") != "claude-sonnet-5-5":
        errs.append("OMC_MODEL_MEDIUM must be 'claude-sonnet-5-5'")
    if env_map.get("OMC_MODEL_LOW") != "claude-sonnet-5-5":
        errs.append("OMC_MODEL_LOW must be 'claude-sonnet-5-5' (zero haiku sprawl)")
    return len(errs) == 0, errs


def compute_claude_fable_1to1_telemetry(
    model_counts: dict[str, int],
    *,
    target_fable_share: float = 0.50,
    band_half_width: float = 0.08,
) -> dict[str, Any]:
    """Compute Claude Code CLI fable-5-2 vs remaining model share against the ~1:1 (50% / 50%) target."""
    clean = {str(k): int(v) for k, v in model_counts.items() if int(v) > 0}
    fable_turns = sum(v for k, v in clean.items() if "fable-5-" in k or k == "fable")
    haiku_turns = sum(v for k, v in clean.items() if "haiku" in k)
    remaining_turns = sum(v for k, v in clean.items() if k != "fable" and "fable-5-" not in k)
    total = fable_turns + remaining_turns
    fable_share = round(fable_turns / total, 4) if total > 0 else target_fable_share
    low_b = round(target_fable_share - band_half_width, 4)
    high_b = round(target_fable_share + band_half_width, 4)
    in_band = low_b <= fable_share <= high_b
    return {
        "schemaVersion": "sota-claude-1to1-telemetry.v1",
        "totalTurns": total,
        "fableTurns": fable_turns,
        "remainingTurns": remaining_turns,
        "haikuTurns": haiku_turns,
        "fableShare": fable_share,
        "remainingShare": round(1.0 - fable_share, 4) if total > 0 else round(1.0 - target_fable_share, 4),
        "allowedBand": (low_b, high_b),
        "within1To1Band": in_band,
    }
