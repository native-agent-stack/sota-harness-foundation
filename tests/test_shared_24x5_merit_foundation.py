"""Tests for ADR-0040: Upstream-First Shared 24/5 Lossless Foundation & Merit Contract."""

from __future__ import annotations

from cc_sota_harness.shared_24x5_merit_foundation import (
    DUAL_MACHINE_MERIT_GOAL_ID,
    PORTABLE_COCKPIT_FAILOVER_HOST,
    PRIMARY_SOVEREIGN_WORKSTATION_HOST,
    SHARED_24X5_LOSSLESS_FOUNDATION,
    SOVEREIGN_ENGINE_PORTS,
    UPSTREAM_PLATFORM_BINDINGS,
    LaneFoundationCheck,
    build_shared_foundation_manifest,
    validate_lane_foundation_contract,
    validate_sovereign_host_authority,
)


def test_shared_foundation_manifest_and_upstream_bindings() -> None:
    mf = build_shared_foundation_manifest()
    assert mf["adr"] == "ADR-0041"
    assert mf["goal_id"] == DUAL_MACHINE_MERIT_GOAL_ID
    assert mf["primary_sovereign_host"] == PRIMARY_SOVEREIGN_WORKSTATION_HOST == "stationary_noesis_win32"
    assert mf["portable_cockpit_host"] == PORTABLE_COCKPIT_FAILOVER_HOST == "portable_mac_m5_max"
    assert mf["upstream_domains_count"] == 6
    assert len(mf["foundation_sha256"]) == 64
    assert SHARED_24X5_LOSSLESS_FOUNDATION["paper_and_live_share_same_foundation"] is True
    assert SHARED_24X5_LOSSLESS_FOUNDATION["workstation_hosts_main_framework_and_trading_engine"] is True
    assert set(SOVEREIGN_ENGINE_PORTS.values()) == {8799, 8787, 8797, 4002, 8798}
    assert set(SHARED_24X5_LOSSLESS_FOUNDATION["active_mac_ports"].values()) == {8799, 8787, 8797, 4002, 8798}
    assert "nautilus_trader" in UPSTREAM_PLATFORM_BINDINGS["event_and_queue_microstructure_sim_s2"]["upstreams"]
    assert "skfolio" in UPSTREAM_PLATFORM_BINDINGS["backtest_and_statistical_falsification_s1"]["upstreams"]


def test_sovereign_workstation_primary_and_portable_mac_failover_authority() -> None:
    # Default: Stationary Noesis is active 24/5 broker host; Portable Mac is read-only cockpit
    ok_primary, errs_primary = validate_sovereign_host_authority(
        active_broker_host="stationary_noesis_win32",
        mac_read_only_radar=True,
        noesis_read_only_radar=False,
    )
    assert ok_primary and not errs_primary

    # Dual active (both submitting orders) fails closed
    bad_dual, errs_dual = validate_sovereign_host_authority(
        active_broker_host="stationary_noesis_win32",
        mac_read_only_radar=False,
        noesis_read_only_radar=False,
    )
    assert not bad_dual
    assert any("PORTABLE_MAC_MUST_BE_READ_ONLY_COCKPIT" in e for e in errs_dual)

    # Explicit Portable Mac failover lease (Noesis read-only/offline) passes
    ok_fo, errs_fo = validate_sovereign_host_authority(
        active_broker_host="portable_mac_m5_max",
        mac_read_only_radar=False,
        noesis_read_only_radar=True,
    )
    assert ok_fo and not errs_fo

    # Unknown host fails closed
    bad_unk, errs_unk = validate_sovereign_host_authority(
        active_broker_host="rogue_box",
        mac_read_only_radar=True,
        noesis_read_only_radar=True,
    )
    assert not bad_unk
    assert any("UNKNOWN_ACTIVE_BROKER_HOST" in e for e in errs_unk)


def test_lane_foundation_gating_and_nan_fail_closed() -> None:
    # 1. Sim & Paper pass ONLY when NEVER_GATED and sharing Lossless Foundation
    ok_sim, errs_sim = validate_lane_foundation_contract(
        LaneFoundationCheck("S1", "SIM", "NEVER_GATED", True, 1.80, 10.0)
    )
    assert ok_sim and not errs_sim

    ok_paper, errs_paper = validate_lane_foundation_contract(
        LaneFoundationCheck("P3", "PAPER", "NEVER_GATED", True, 1.90, 10.0)
    )
    assert ok_paper and not errs_paper

    bad_gated_paper, errs_gp = validate_lane_foundation_contract(
        LaneFoundationCheck("P2", "PAPER", "MANUAL_APPROVAL_GATE", True, 1.50, 10.0)
    )
    assert not bad_gated_paper
    assert any("SIM_AND_PAPER_MUST_BE_NEVER_GATED" in e for e in errs_gp)

    # 2. Live passes ONLY when PROVEN_AUTOMATION_ONLY_STARTING_WITH_LOSSLESS_FOUNDATION & <= 2.00% stop & >= 10% exit reserve
    ok_live, errs_live = validate_lane_foundation_contract(
        LaneFoundationCheck("L5", "LIVE", "PROVEN_AUTOMATION_ONLY_STARTING_WITH_LOSSLESS_FOUNDATION", True, 1.65, 10.0)
    )
    assert ok_live and not errs_live

    # 3. NaN stop or <10% exit reserve or custom non-upstream reinvention fails closed
    bad_nan, errs_nan = validate_lane_foundation_contract(
        LaneFoundationCheck(
            "L5", "LIVE", "PROVEN_AUTOMATION_ONLY_STARTING_WITH_LOSSLESS_FOUNDATION", True, float("nan"), 5.0, False
        )
    )
    assert not bad_nan
    assert len(errs_nan) == 3
