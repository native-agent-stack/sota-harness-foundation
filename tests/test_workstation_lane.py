"""Unit and Hypothesis property tests for the Dual-Machine Orca Workstation Lane (ADR-0020)."""
from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cc_sota_harness.workstation_lane import (
    PORTABLE_MAC_MAX_THREADS_AC,
    PORTABLE_MAC_MAX_THREADS_BATTERY,
    PORTABLE_MAC_MAX_THREADS_LOW_BATTERY,
    STATIONARY_NOESIS_MAX_THREADS,
    HostTelemetry,
    WorkloadKind,
    WorkstationTopologyMode,
    build_orca_coop_sync_plan,
    classify_topology_mode,
    enforce_workstation_wsl_and_gateway_guard,
    filter_lease_safe_sync_repos,
    portable_thread_budget,
    resolve_workstation_placement,
    validate_dual_workstation_manifest,
    validate_headless_orca_serve_flags,
)


def test_dual_workstation_manifest_validates_18_noesis_repos() -> None:
    manifest, errors = validate_dual_workstation_manifest()
    assert errors == []
    repos = manifest["workstations"]["stationary_noesis_heavy"]["provisionedOrcaRepos"]
    assert len(repos) == 18
    assert "cc-sota-harness" in repos
    assert "sota-harness-foundation" in repos
    assert "sota-mover-ranker" in repos


@given(
    b_low=st.floats(min_value=0.0, max_value=34.9, allow_nan=False, allow_infinity=False),
    b_mid=st.floats(min_value=35.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    b_any=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_portable_thread_budget_monotonicity(b_low: float, b_mid: float, b_any: float) -> None:
    t_low = portable_thread_budget(on_ac_power=False, battery_pct=b_low)
    t_mid = portable_thread_budget(on_ac_power=False, battery_pct=b_mid)
    t_ac = portable_thread_budget(on_ac_power=True, battery_pct=b_any)
    assert t_low == PORTABLE_MAC_MAX_THREADS_LOW_BATTERY
    assert t_mid == PORTABLE_MAC_MAX_THREADS_BATTERY
    assert t_ac == PORTABLE_MAC_MAX_THREADS_AC
    assert 0 < t_low <= t_mid <= t_ac < 18


@given(
    batt=st.floats(min_value=35.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    on_ac=st.booleans(),
)
def test_property_portable_heavy_research_never_fails_when_carried_offline(batt: float, on_ac: bool) -> None:
    tel = HostTelemetry(on_ac_power=on_ac, battery_pct=batt, paired_host_reachable=False, paired_rtt_ms=None)
    dec = resolve_workstation_placement(tel, WorkloadKind.HEAVY_PREWALL_RESEARCH)
    assert dec.approved is True
    assert dec.target_host == "portable_mac_lead"
    assert dec.orca_selector == "--host local"
    assert dec.allocated_threads in (PORTABLE_MAC_MAX_THREADS_BATTERY, PORTABLE_MAC_MAX_THREADS_AC)


def test_docked_offloads_combinatorial_to_noesis_and_battery_mesh_offloads_research() -> None:
    docked = HostTelemetry(on_ac_power=True, battery_pct=100.0, paired_host_reachable=True, paired_rtt_ms=12.4)
    assert classify_topology_mode(docked) == WorkstationTopologyMode.DUAL_MESH_DOCKED

    batch_dec = resolve_workstation_placement(
        docked,
        WorkloadKind.COMBINATORIAL_GPU_BATCH,
        repo_name="sota-harness-foundation",
        remote_repo_id="3c64b92a-ec58-4e82-b85d-42bad91048b1",
    )
    assert batch_dec.approved is True
    assert batch_dec.target_host == "stationary_noesis_heavy"
    assert batch_dec.allocated_threads == STATIONARY_NOESIS_MAX_THREADS
    assert "--on 100.110.115.22" in batch_dec.orca_command_template
    assert "id:3c64b92a-ec58-4e82-b85d-42bad91048b1" in batch_dec.orca_command_template

    batt_mesh = HostTelemetry(on_ac_power=False, battery_pct=62.0, paired_host_reachable=True, paired_rtt_ms=18.0)
    res_dec = resolve_workstation_placement(batt_mesh, WorkloadKind.HEAVY_PREWALL_RESEARCH)
    assert res_dec.target_host == "stationary_noesis_heavy"
    assert res_dec.allocated_threads == STATIONARY_NOESIS_MAX_THREADS


def test_low_battery_defers_offline_combinatorial_and_blocks_roaming_broker() -> None:
    low_offline = HostTelemetry(on_ac_power=False, battery_pct=18.0, paired_host_reachable=False)
    batch_dec = resolve_workstation_placement(low_offline, WorkloadKind.COMBINATORIAL_GPU_BATCH)
    assert batch_dec.approved is False

    broker_dec = resolve_workstation_placement(
        low_offline,
        WorkloadKind.PAPER_BROKER_24X5,
        candidate_broker_host="portable_mac_lead",
    )
    assert broker_dec.approved is False
    assert "Lesson 7" in broker_dec.reason


def test_dual_machine_broker_split_brain_hard_refused() -> None:
    tel = HostTelemetry(
        on_ac_power=True,
        battery_pct=100.0,
        paired_host_reachable=True,
        paired_rtt_ms=4.2,
        active_broker_host="portable_mac_lead",
    )
    with pytest.raises(PermissionError, match="split-brain hard-refused"):
        resolve_workstation_placement(
            tel,
            WorkloadKind.PAPER_BROKER_24X5,
            candidate_broker_host="stationary_noesis_heavy",
        )


def test_adr_0021_wsl_shared_vm_and_gateway_guards() -> None:
    enforce_workstation_wsl_and_gateway_guard("wsl -d meridian -e pytest -q", {"ANTHROPIC_BASE_URL": "http://127.0.0.1:20128"})

    with pytest.raises(PermissionError, match="wsl --shutdown"):
        enforce_workstation_wsl_and_gateway_guard("wsl --shutdown")

    with pytest.raises(PermissionError, match="sextant"):
        enforce_workstation_wsl_and_gateway_guard("wsl.exe --unregister sextant")

    # Explicit Stage B owner cutover authorization permits quiesced WSL cutover while keeping gateway/OAuth guards active
    enforce_workstation_wsl_and_gateway_guard("wsl --shutdown", stage_b_cutover_authorized=True)
    enforce_workstation_wsl_and_gateway_guard("wsl.exe --unregister sextant", stage_b_cutover_authorized=True)
    with pytest.raises(PermissionError, match="Tailscale Serve"):
        enforce_workstation_wsl_and_gateway_guard(
            "wsl --shutdown",
            tailscale_serve_gateway_unauthenticated=True,
            stage_b_cutover_authorized=True,
        )

    with pytest.raises(PermissionError, match="Tailscale Serve"):
        enforce_workstation_wsl_and_gateway_guard(tailscale_serve_gateway_unauthenticated=True)

    with pytest.raises(PermissionError, match="CLAUDE_CODE_OAUTH_TOKEN"):
        enforce_workstation_wsl_and_gateway_guard(
            env={"ANTHROPIC_BASE_URL": "http://127.0.0.1:20128", "CLAUDE_CODE_OAUTH_TOKEN": "oauth-redacted"}
        )


def test_adr_0022_orca_coop_sync_plan_enforces_org_and_uuid() -> None:
    plan = build_orca_coop_sync_plan(converged_sha="e5eb9ba000000000")
    assert "--comment" in plan["set_comment"]
    assert "e5eb9ba000" in plan["set_comment"][-2]
    assert "--url" in plan["add_reference"]

    with pytest.raises(ValueError, match="native-agent-stack"):
        build_orca_coop_sync_plan(reference_url="https://example.com/outside")


def test_adr_0025_headless_orca_serve_and_lease_safe_sync_guards() -> None:
    validate_headless_orca_serve_flags(
        ["orca", "serve", "--host", "100.110.115.22", "--port", "6770", "--no-pairing", "--refuse-public"]
    )
    with pytest.raises(PermissionError, match="--refuse-public"):
        validate_headless_orca_serve_flags(["orca", "serve", "--host", "100.110.115.22", "--no-pairing"])
    with pytest.raises(PermissionError, match="wildcard bind"):
        validate_headless_orca_serve_flags(
            ["orca", "serve", "--host", "0.0.0.0", "--no-pairing", "--refuse-public"]
        )

    safe, skipped = filter_lease_safe_sync_repos(
        ["sota-harness-foundation", "sota-mover-ranker", "meridian"],
        remote_active_leases=[{"repo": "sota-mover-ranker", "lease_key": "sota-mover-ranker::agy-noesis-24x5"}],
        dirty_repos={"meridian"},
    )
    assert safe == ["sota-harness-foundation"]
    assert skipped == {
        "sota-mover-ranker": "remote_lease:sota-mover-ranker::agy-noesis-24x5",
        "meridian": "dirty_worktree",
    }
