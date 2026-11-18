"""Tests for ADR-0040: Upstream-First Shared 24/5 Lossless Foundation & Merit Contract."""

from __future__ import annotations

from cc_sota_harness.shared_24x5_merit_foundation import (
    DUAL_MACHINE_MERIT_GOAL_ID,
    SHARED_24X5_LOSSLESS_FOUNDATION,
    UPSTREAM_PLATFORM_BINDINGS,
    LaneFoundationCheck,
    build_shared_foundation_manifest,
    validate_lane_foundation_contract,
)


def test_shared_foundation_manifest_and_upstream_bindings() -> None:
    mf = build_shared_foundation_manifest()
    assert mf["adr"] == "ADR-0040"
    assert mf["goal_id"] == DUAL_MACHINE_MERIT_GOAL_ID
    assert mf["upstream_domains_count"] == 6
    assert len(mf["foundation_sha256"]) == 64
    assert SHARED_24X5_LOSSLESS_FOUNDATION["paper_and_live_share_same_foundation"] is True
    assert set(SHARED_24X5_LOSSLESS_FOUNDATION["active_mac_ports"].values()) == {8799, 8787, 8797, 4002, 8798}
    assert "nautilus_trader" in UPSTREAM_PLATFORM_BINDINGS["event_and_queue_microstructure_sim_s2"]["upstreams"]
    assert "skfolio" in UPSTREAM_PLATFORM_BINDINGS["backtest_and_statistical_falsification_s1"]["upstreams"]


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
