"""Unit, Property-Based (Hypothesis) & Red-Team Firewall Tests for `ADR-0045` TradingView Landscape Contract."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cc_sota_harness.redteam_and_skill_eval import run_redteam_firewall_audit
from cc_sota_harness.tv_multilayout_lossless_contract import (
    ADR0022_MAX_STOP_PCT_FLOAT,
    ALPACA_ALGO_PLUS_EXIT_RESERVE_RPM,
    ALPACA_ALGO_PLUS_MAX_RPM,
    ALPACA_HTTP429_EXIT_RESERVE_RPM,
    ALPACA_HTTP429_FALLBACK_RPM,
    CANONICAL_TV_MULTI_LAYOUTS,
    FORBIDDEN_LIVE_HOSTS,
    FORBIDDEN_LIVE_PORTS,
    IBKR_PAPER_EXIT_RESERVE_MPM,
    IBKR_PAPER_MAX_MPM,
    LARGECAP_BE_ARM_MAX_BPS,
    LARGECAP_BE_ARM_MIN_BPS,
    LARGECAP_MAX_TRAIL_BPS,
    LARGECAP_MIN_TRAIL_BPS,
    TV_LIBRARY_LANDSCAPE_STACK,
    UNCAPPED_QUICKBAR_CHIPS,
    DualLane1000RpmRateBudget,
    build_tv_multilayout_foundation_manifest,
    classify_cap_liquidity_tier,
    compute_largecap_micro_trail_plan,
    evaluate_suitable_timing_reentry,
    quantize_rule612_price,
    validate_tv_preset_and_route_firewall,
    venue_min_trail_bps,
)


def _sample_six_uncapped_presets() -> list[dict]:
    return [
        {"chip": "P", "tv_ticket_config": {"quantity_type": "Shares", "tp_enabled": False, "sl_pct_price": None}},
        {"chip": "L", "tv_ticket_config": {"quantity_type": "Shares", "tp_enabled": False, "sl_pct_price": None}},
        {"chip": "M", "tv_ticket_config": {"quantity_type": "Shares", "tp_enabled": False, "sl_pct_price": None}},
        {"chip": "B", "tv_ticket_config": {"quantity_type": "Shares", "tp_enabled": False, "sl_pct_price": 1.60}},
        {"chip": "S", "tv_ticket_config": {"quantity_type": "Shares", "tp_enabled": False, "sl_pct_price": 0.50}},
        {"chip": "O", "tv_ticket_config": {"quantity_type": "Shares", "tp_enabled": False, "sl_pct_price": 1.60}},
    ]


def test_library_landscape_and_five_layouts_governance_invariants() -> None:
    manifest = build_tv_multilayout_foundation_manifest()
    assert manifest["library_landscape_count"] == 14
    assert manifest["multi_layouts_count"] == 5
    assert manifest["order_authority_on_visual_surfaces"] is False
    assert manifest["visual_artifacts_may_bind_alert_or_webhook"] is False
    assert manifest["standalone_alpha_claim"] is False
    assert manifest["promotion_track"] == "PROTECTIVE_FILTER_OR_GOVERNANCE"
    assert len(manifest["manifest_sha256"]) == 64

    # Deterministic SHA-256 across repeated builds
    assert manifest["manifest_sha256"] == build_tv_multilayout_foundation_manifest()["manifest_sha256"]

    # Every library explicitly audited into the 4 ADR-0017 capability classes with zero order authority
    valid_classes = {
        "PINNED_INTEGRATE",
        "OPTIONAL_READ_ONLY_OR_OFFLINE_RESEARCH",
        "PHILOSOPHY_ONLY",
        "HARD_REFUSED_EXECUTION_SAAS",
    }
    ids = set()
    for lib in TV_LIBRARY_LANDSCAPE_STACK:
        assert lib["capability_class"] in valid_classes
        assert lib["order_authority"] is False
        assert lib["visual_may_bind_webhook"] is False
        ids.add(lib["library_id"])
    assert {
        "lightweight-charts",
        "perspective",
        "openbb-workspace-backend",
        "tradingview-official-cloud-mcp",
        "pine-script-v6-libraries",
        "tvscreener",
        "pynecore",
        "pinets",
        "lightweight-charts-python",
        "tradingview-advanced-charts-trading-platform",
        "third-party-tv-webhook-saas-and-openalgo",
    }.issubset(ids)

    # Every layout enforces >= 92% unobstructed candles and zero order authority
    layout_names = [ly["tv_cloud_layout_name"] for ly in CANONICAL_TV_MULTI_LAYOUTS]
    assert len(set(layout_names)) == 5
    for ly in CANONICAL_TV_MULTI_LAYOUTS:
        assert ly["unobstructed_candle_area_min_pct"] >= 92.0
        assert ly["order_authority"] is False


def test_largecap_6_to_14_bps_micro_trail_sub_venue_fast_sell_and_green_floor() -> None:
    # NVDA-like mega-cap ($140, 1.5 bps spread, 0.06% 1m ATR): sub-venue < 10 bps micro-trail active!
    plan = compute_largecap_micro_trail_plan(
        entry_px=140.00,
        current_px=140.55,
        extreme_px=140.80,
        side="long",
        adv_20d_usd=25_000_000_000.0,
        atr_1m_pct=0.06,
        spread_bps=1.5,
        ofi_pct=-7.5,  # Adverse flow triggers climax tightening!
    )
    assert plan.liquidity_tier == "MEGA_LARGE_CAP"
    assert plan.gain_lock_armed is True
    assert LARGECAP_BE_ARM_MIN_BPS <= plan.be_arm_bps <= LARGECAP_BE_ARM_MAX_BPS
    assert LARGECAP_MIN_TRAIL_BPS <= plan.target_trail_bps <= LARGECAP_MAX_TRAIL_BPS
    assert plan.sub_venue_micro_trail_active is True
    assert plan.native_broker_trail_bps >= venue_min_trail_bps(140.80)
    assert plan.take_profit_cap_enabled is False
    assert plan.locked_gain_bps > 0.0
    assert plan.fast_sell_triggered is True
    assert plan.fast_sell_limit_px is not None
    # Green-floor protection: fast-sell limit stays >= entry + 4 bps on attempt 0
    assert plan.fast_sell_limit_px >= Decimal("140.06")

    # Monotonicity check: lower current/extreme NEVER loosens prev_stop_px
    step2 = compute_largecap_micro_trail_plan(
        entry_px=140.00,
        current_px=140.30,
        extreme_px=140.40,
        prev_stop_px=plan.active_stop_px,
        side="long",
        adv_20d_usd=25_000_000_000.0,
        atr_1m_pct=0.06,
        spread_bps=1.5,
        ofi_pct=0.0,
    )
    assert step2.active_stop_px >= plan.active_stop_px

    # Symmetric Short Mega-Cap micro-trail
    s_plan = compute_largecap_micro_trail_plan(
        entry_px=500.00,
        current_px=497.50,
        extreme_px=497.00,
        side="short",
        adv_20d_usd=18_000_000_000.0,
        atr_1m_pct=0.05,
        spread_bps=1.2,
        ofi_pct=8.0,
    )
    assert s_plan.liquidity_tier == "MEGA_LARGE_CAP"
    assert LARGECAP_MIN_TRAIL_BPS <= s_plan.target_trail_bps <= LARGECAP_MAX_TRAIL_BPS
    assert s_plan.gain_lock_armed is True
    assert s_plan.locked_gain_bps > 0.0
    assert s_plan.fast_sell_triggered is True
    assert s_plan.fast_sell_limit_px is not None
    assert s_plan.fast_sell_limit_px <= Decimal("499.80")


def test_suitable_timing_fast_reentry_windows_and_hard_guards() -> None:
    # Long Window A: Large-Cap 15 bps pullback absorption after 14s dwell
    win_a = evaluate_suitable_timing_reentry(
        strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
        exit_px=140.00,
        live_px=139.79,
        vwap_px=139.60,
        retrace_extreme_px=139.75,
        elapsed_sec=14.0,
        ofi_pct=2.2,
        spread_bps=2.0,
        wave_num=2,
        trail_ended=True,
        side="long",
        is_mega_large_cap=True,
    )
    assert win_a.approved is True
    assert win_a.window == "WINDOW_A_PULLBACK_ABSORPTION"
    assert win_a.recommended_preset_chip == "S"

    # Too early (< 12s after full exit) must wait
    too_early = evaluate_suitable_timing_reentry(
        strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
        exit_px=140.00,
        live_px=139.79,
        vwap_px=139.60,
        retrace_extreme_px=139.75,
        elapsed_sec=8.0,
        ofi_pct=2.2,
        spread_bps=2.0,
        wave_num=2,
        trail_ended=True,
        side="long",
        is_mega_large_cap=True,
    )
    assert too_early.approved is False
    assert too_early.window == "WAITING"

    # Partial 50/50 core harvest (trail_ended=False) allows faster >= 6s Window A
    partial_ok = evaluate_suitable_timing_reentry(
        strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
        exit_px=140.00,
        live_px=139.79,
        vwap_px=139.60,
        retrace_extreme_px=139.75,
        elapsed_sec=8.0,
        ofi_pct=2.2,
        spread_bps=2.0,
        wave_num=2,
        trail_ended=False,
        side="long",
        is_mega_large_cap=True,
    )
    assert partial_ok.approved is True

    # Window B tight coil continuation at 40s
    win_b = evaluate_suitable_timing_reentry(
        strategy_id="ZARATTINI_2024_5M_ORB",
        exit_px=140.00,
        live_px=140.15,
        vwap_px=139.90,
        retrace_extreme_px=139.98,
        elapsed_sec=40.0,
        ofi_pct=4.2,
        spread_bps=3.0,
        wave_num=3,
        trail_ended=True,
        side="long",
        is_mega_large_cap=True,
    )
    assert win_b.approved is True
    assert win_b.window == "WINDOW_B_TIGHT_COIL_CONTINUATION"

    # Short Window A bounce rejection requires ETB + SSR
    short_ok = evaluate_suitable_timing_reentry(
        strategy_id="VIX_SPIKE_AND_CRUSH_REGIME_SURFER",
        exit_px=100.00,
        live_px=100.16,
        vwap_px=100.30,
        retrace_extreme_px=100.20,
        elapsed_sec=15.0,
        ofi_pct=-2.5,
        spread_bps=3.0,
        wave_num=2,
        trail_ended=True,
        side="short",
        is_mega_large_cap=True,
        easy_to_borrow=True,
        shortable=True,
        ssr_uptick_compliant=True,
    )
    assert short_ok.approved is True
    assert short_ok.window == "WINDOW_A_BOUNCE_REJECTION"

    # Fail-closed checks: HTB short, ADR-0064 quarantine, wave 4, R3a stopout lock, daily scratch loss, dilution, NaN
    assert not evaluate_suitable_timing_reentry(
        strategy_id="VIX_SPIKE_AND_CRUSH_REGIME_SURFER",
        exit_px=100.0,
        live_px=100.16,
        vwap_px=100.30,
        retrace_extreme_px=100.20,
        elapsed_sec=15.0,
        ofi_pct=-2.5,
        spread_bps=3.0,
        side="short",
        easy_to_borrow=False,
    ).approved
    assert (
        "QUARANTINED_ADR0064"
        in evaluate_suitable_timing_reentry(
            strategy_id="BLIND_WAVE2_REENTRY",
            exit_px=140.0,
            live_px=139.7,
            vwap_px=139.6,
            retrace_extreme_px=139.7,
            elapsed_sec=20.0,
            ofi_pct=3.0,
            spread_bps=2.0,
        ).reason
    )
    assert (
        evaluate_suitable_timing_reentry(
            strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
            exit_px=140.0,
            live_px=139.7,
            vwap_px=139.6,
            retrace_extreme_px=139.7,
            elapsed_sec=20.0,
            ofi_pct=3.0,
            spread_bps=2.0,
            wave_num=4,
        ).reason
        == "MAX_3_WAVES_ANTI_CHURN"
    )
    assert (
        evaluate_suitable_timing_reentry(
            strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
            exit_px=140.0,
            live_px=139.7,
            vwap_px=139.6,
            retrace_extreme_px=139.7,
            elapsed_sec=20.0,
            ofi_pct=3.0,
            spread_bps=2.0,
            symbol_daily_stopouts=2,
        ).reason
        == "R3A_SYMBOL_DAILY_STOPOUT_LOCK"
    )
    assert (
        evaluate_suitable_timing_reentry(
            strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
            exit_px=140.0,
            live_px=139.7,
            vwap_px=139.6,
            retrace_extreme_px=139.7,
            elapsed_sec=20.0,
            ofi_pct=3.0,
            spread_bps=2.0,
            account_daily_realized_bps=-75.0,
        ).reason
        == "DAILY_SCRATCH_LOSS_BREAKER_HALTED"
    )
    assert (
        evaluate_suitable_timing_reentry(
            strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
            exit_px=140.0,
            live_px=139.7,
            vwap_px=139.6,
            retrace_extreme_px=139.7,
            elapsed_sec=20.0,
            ofi_pct=float("nan"),
            spread_bps=2.0,
        ).reason
        == "NONFINITE_INPUT"
    )


def test_1000rpm_alpaca_http429_non_starvation_and_ibkr_3000mpm_firewall() -> None:
    now = [1000.0]
    rb = DualLane1000RpmRateBudget(clock=lambda: now[0])

    # Exhaust all 900 entry slots; 901st entry blocked, all 100 exit reserve slots succeed!
    entries_ok = sum(1 for _ in range(950) if rb.acquire_alpaca(is_protective_exit=False))
    assert entries_ok == ALPACA_ALGO_PLUS_MAX_RPM - ALPACA_ALGO_PLUS_EXIT_RESERVE_RPM == 900
    exits_ok = sum(1 for _ in range(120) if rb.acquire_alpaca(is_protective_exit=True))
    assert exits_ok == ALPACA_ALGO_PLUS_EXIT_RESERVE_RPM == 100

    # HTTP-429 mid-burst: fresh bucket with 400 pre-429 entries still guarantees full 20/min exit reserve!
    rb2 = DualLane1000RpmRateBudget(clock=lambda: now[0])
    assert sum(1 for _ in range(400) if rb2.acquire_alpaca(is_protective_exit=False)) == 400
    rb2.note_alpaca_http_429()
    assert rb2.alpaca_effective_rpm == ALPACA_HTTP429_FALLBACK_RPM == 200
    assert rb2.acquire_alpaca(is_protective_exit=False) is False
    post_429_exits = sum(1 for _ in range(25) if rb2.acquire_alpaca(is_protective_exit=True))
    assert post_429_exits == ALPACA_HTTP429_EXIT_RESERVE_RPM == 20

    # IBKR :4002 enforces 50/sec (45 entry + 5 exit reserve) & 3000/min (2700 + 300)
    assert sum(1 for _ in range(50) if rb.acquire_ibkr(is_protective_exit=False)) == 45
    assert sum(1 for _ in range(10) if rb.acquire_ibkr(is_protective_exit=True)) == 5
    assert rb.ibkr_max_mpm == IBKR_PAPER_MAX_MPM
    assert rb.ibkr_exit_reserve_mpm == IBKR_PAPER_EXIT_RESERVE_MPM

    # TV Cloud MCP capped at 18/min
    assert sum(1 for _ in range(25) if rb.acquire_tv_cloud_mcp()) == 18

    # Live IBKR ports and malformed constructor budgets hard-refused
    for bad_port in FORBIDDEN_LIVE_PORTS:
        with pytest.raises(ValueError, match="IBKR Paper Firewall"):
            DualLane1000RpmRateBudget(ibkr_port=bad_port)
    with pytest.raises(ValueError, match="alpaca_exit_reserve_rpm"):
        DualLane1000RpmRateBudget(alpaca_max_rpm=100, alpaca_exit_reserve_rpm=150)
    with pytest.raises(ValueError, match="ibkr_max_mpm"):
        DualLane1000RpmRateBudget(ibkr_max_mpm=0)
    with pytest.raises(ValueError, match="ibkr_max_per_sec"):
        DualLane1000RpmRateBudget(ibkr_max_per_sec=1)
    with pytest.raises(ValueError, match="tv_mcp_max_rpm"):
        DualLane1000RpmRateBudget(tv_mcp_max_rpm=99)


def test_preset_and_route_firewall_blocks_live_ports_saas_and_fixed_tp() -> None:
    presets = _sample_six_uncapped_presets()
    ok, errs = validate_tv_preset_and_route_firewall(presets=presets, target_port=8787)
    assert ok is True and errs == []

    # Reject fixed TP on any preset (ADR-0063)
    bad_tp = _sample_six_uncapped_presets()
    bad_tp[3]["tv_ticket_config"]["tp_enabled"] = True
    ok_tp, errs_tp = validate_tv_preset_and_route_firewall(presets=bad_tp, target_port=8787)
    assert not ok_tp and any("PRESET_FIXED_TP_FORBIDDEN_ADR0063" in e for e in errs_tp)

    # Reject live hosts, live ports, and third-party SaaS bridges
    for bad_host in FORBIDDEN_LIVE_HOSTS:
        ok_h, errs_h = validate_tv_preset_and_route_firewall(presets=presets, target_port=8787, target_host=bad_host)
        assert not ok_h and any("LIVE_HOST_HARD_REFUSED" in e for e in errs_h)
    for bad_port in FORBIDDEN_LIVE_PORTS:
        ok_p, errs_p = validate_tv_preset_and_route_firewall(presets=presets, target_port=bad_port)
        assert not ok_p and any("LIVE_PORT_HARD_REFUSED" in e for e in errs_p)
    for bad_saas in ("SignalStack", "TradersPost", "marketcalls/openalgo", "PineConnector"):
        ok_s, errs_s = validate_tv_preset_and_route_firewall(presets=presets, target_port=8787, bridge_name=bad_saas)
        assert not ok_s and any("HARD_REFUSED_EXECUTION_SAAS" in e for e in errs_s)


def test_redteam_firewall_audit_clean_on_contract_module() -> None:
    import json
    from pathlib import Path

    mod_path = Path(__file__).resolve().parents[1] / "src" / "cc_sota_harness" / "tv_multilayout_lossless_contract.py"
    audit = run_redteam_firewall_audit(
        mod_path.read_text(encoding="utf-8"),
        context="tv_multilayout_lossless_contract",
        hard_stop_pct=1.25,
    )
    assert audit["passed"] is True, f"Unexpected red-team findings: {audit['findings']}"

    manifest_json = json.dumps(build_tv_multilayout_foundation_manifest(), sort_keys=True)
    m_audit = run_redteam_firewall_audit(
        manifest_json,
        context="tv_multilayout_foundation_manifest",
        hard_stop_pct=1.60,
    )
    assert m_audit["passed"] is True, f"Unexpected manifest red-team findings: {m_audit['findings']}"


@settings(max_examples=1500, deadline=None)
@given(
    entry_px=st.floats(min_value=5.0, max_value=2500.0, allow_nan=False, allow_infinity=False),
    mfe_delta_bps=st.floats(min_value=0.0, max_value=300.0, allow_nan=False, allow_infinity=False),
    pullback_frac=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    spread_bps=st.floats(min_value=0.5, max_value=8.0, allow_nan=False, allow_infinity=False),
    atr_1m_pct=st.floats(min_value=0.02, max_value=0.12, allow_nan=False, allow_infinity=False),
    side=st.sampled_from(["long", "short"]),
    lev_x=st.sampled_from([1.0, 2.0, 4.0]),
)
def test_hypothesis_largecap_micro_trail_monotonicity_and_adr0022_bounds(
    entry_px: float,
    mfe_delta_bps: float,
    pullback_frac: float,
    spread_bps: float,
    atr_1m_pct: float,
    side: str,
    lev_x: float,
) -> None:
    mult = mfe_delta_bps / 10_000.0
    if side == "long":
        extreme_px = entry_px * (1.0 + mult)
        current_px = entry_px + (extreme_px - entry_px) * (1.0 - pullback_frac)
    else:
        extreme_px = max(0.50, entry_px * (1.0 - mult))
        current_px = entry_px - (entry_px - extreme_px) * (1.0 - pullback_frac)

    plan1 = compute_largecap_micro_trail_plan(
        entry_px=entry_px,
        current_px=current_px,
        extreme_px=extreme_px,
        side=side,
        adv_20d_usd=1_000_000_000.0,
        atr_1m_pct=atr_1m_pct,
        spread_bps=spread_bps,
        position_leverage_x=lev_x,
        max_initial_stop_pct=1.25,
    )
    assert plan1.liquidity_tier == "MEGA_LARGE_CAP"
    assert LARGECAP_MIN_TRAIL_BPS <= plan1.target_trail_bps <= LARGECAP_MAX_TRAIL_BPS
    assert LARGECAP_BE_ARM_MIN_BPS <= plan1.be_arm_bps <= LARGECAP_BE_ARM_MAX_BPS
    assert plan1.realized_risk_from_entry_bps <= ADR0022_MAX_STOP_PCT_FLOAT * 100.0 + 1e-6
    assert plan1.take_profit_cap_enabled is False
    if lev_x >= 2.0:
        assert plan1.realized_risk_from_entry_bps * lev_x <= 135.0 + 0.5

    # Monotonic ratchet invariant on second step
    plan2 = compute_largecap_micro_trail_plan(
        entry_px=entry_px,
        current_px=current_px,
        extreme_px=extreme_px,
        prev_stop_px=plan1.active_stop_px,
        side=side,
        adv_20d_usd=1_000_000_000.0,
        atr_1m_pct=atr_1m_pct,
        spread_bps=spread_bps,
        position_leverage_x=lev_x,
        max_initial_stop_pct=1.25,
    )
    if side == "long":
        assert plan2.active_stop_px >= plan1.active_stop_px
    else:
        assert plan2.active_stop_px <= plan1.active_stop_px


@settings(max_examples=1000, deadline=None)
@given(
    px=st.floats(min_value=0.10, max_value=5000.0, allow_nan=False, allow_infinity=False),
)
def test_hypothesis_rule612_quantization_grid_and_dollar_crossing(px: float) -> None:
    q = quantize_rule612_price(px)
    assert q > Decimal("0")
    if q >= Decimal("1.00"):
        assert (q * Decimal("100")) == (q * Decimal("100")).to_integral_value()
    else:
        assert (q * Decimal("10000")) == (q * Decimal("10000")).to_integral_value()
    assert math.isfinite(venue_min_trail_bps(max(px, 0.05)))
    assert set(UNCAPPED_QUICKBAR_CHIPS) == {"P", "L", "M", "B", "S", "O"}
    assert classify_cap_liquidity_tier(adv_20d_usd=600_000_000.0, atr_1m_pct=0.09, spread_bps=2.0) == "MEGA_LARGE_CAP"


def test_falsifier_pass2_p0_p1_p2_regression_suite() -> None:
    # P0-1: Sub-tick rounding collapse never fires Tick-1 self-liquidation across $0.05..$16.66 (long & short)
    for px in ("0.06", "0.15", "1.00", "1.01", "5.00", "9.99", "10.00", "12.00", "16.00"):
        for side in ("long", "short"):
            p = compute_largecap_micro_trail_plan(
                entry_px=px,
                current_px=px,
                extreme_px=px,
                side=side,
                adv_20d_usd=1e9,
                atr_1m_pct=0.04,
                spread_bps=2.0,
                max_initial_stop_pct=1.60,
            )
            assert p.fast_sell_triggered is False, f"Tick-1 self-liquidation at px={px} side={side}: {p}"
            assert (p.active_stop_px < Decimal(px)) if side == "long" else (p.active_stop_px > Decimal(px))

    # P0-2: Sub-$0.05 crash never emits long sell limit > current_px and never crashes short venue_min_trail_bps
    p_long_crash = compute_largecap_micro_trail_plan(
        entry_px="0.06",
        current_px="0.03",
        extreme_px="0.06",
        side="long",
        adv_20d_usd=50_000_000.0,
        atr_1m_pct=0.50,
        spread_bps=10.0,
    )
    assert p_long_crash.fast_sell_triggered is True
    assert p_long_crash.fast_sell_limit_px is not None and p_long_crash.fast_sell_limit_px <= Decimal("0.03")

    p_short_crash = compute_largecap_micro_trail_plan(
        entry_px="0.06",
        current_px="0.04",
        extreme_px="0.04",
        side="short",
        adv_20d_usd=50_000_000.0,
        atr_1m_pct=0.50,
        spread_bps=10.0,
    )
    assert p_short_crash.active_stop_px > Decimal("0.04")

    # P1-1: Green-floor never pins above NBBO bid on wide spread or blocks attempt 1..2 urgency sweeps
    for att, max_lim in ((0, Decimal("99.98")), (1, Decimal("99.62")), (2, Decimal("99.42"))):
        p_att = compute_largecap_micro_trail_plan(
            entry_px="100.00",
            current_px="100.04",
            extreme_px="100.20",
            side="long",
            spread_bps=8.0,
            atr_1m_pct=0.05,
            exit_attempt_num=att,
        )
        assert p_att.fast_sell_triggered is True
        assert p_att.fast_sell_limit_px is not None and p_att.fast_sell_limit_px <= max_lim

    # P1-2: HTTP-429 never shrinks custom reserve or expands entry_cap when already <= 200
    rb_custom = DualLane1000RpmRateBudget(alpaca_max_rpm=200, alpaca_exit_reserve_rpm=50)
    rb_custom.note_alpaca_http_429()
    assert rb_custom.alpaca_effective_rpm == 200
    assert rb_custom.alpaca_effective_exit_reserve_rpm == 50

    # P1-3: Re-entry fail-closed on NaN counters, impossible Window B retrace, crash wick, paused non-core, default short
    assert not evaluate_suitable_timing_reentry(
        strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
        exit_px=100.0,
        live_px=99.80,
        vwap_px=99.60,
        retrace_extreme_px=99.75,
        elapsed_sec=20.0,
        ofi_pct=3.0,
        spread_bps=2.0,
        symbol_daily_stopouts=cast(Any, float("nan")),
    ).approved
    assert not evaluate_suitable_timing_reentry(
        strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
        exit_px=100.0,
        live_px=100.0,
        vwap_px=99.9,
        retrace_extreme_px=105.0,
        elapsed_sec=45.0,
        ofi_pct=4.0,
        spread_bps=2.0,
    ).approved
    assert not evaluate_suitable_timing_reentry(
        strategy_id="BJZZ_SUBPENNY_INST_DARK_SWEEP",
        exit_px=100.0,
        live_px=100.05,
        vwap_px=99.9,
        retrace_extreme_px=50.0,
        elapsed_sec=20.0,
        ofi_pct=4.0,
        spread_bps=2.0,
    ).approved
    assert (
        "QUARANTINED_ADR0064"
        in evaluate_suitable_timing_reentry(
            strategy_id="MY_FLOW_VELOCITY_CAPITAL_RECYCLE_V2",
            exit_px=100.0,
            live_px=99.8,
            vwap_px=99.6,
            retrace_extreme_px=99.75,
            elapsed_sec=20.0,
            ofi_pct=3.0,
            spread_bps=2.0,
        ).reason
    )
    assert (
        "NON_CORE_STRATEGY_PAUSED_ADR0064"
        in evaluate_suitable_timing_reentry(
            strategy_id="QLIB_ALPHA158_LGBM_XSEC_BENCHMARK",
            exit_px=100.0,
            live_px=99.8,
            vwap_px=99.6,
            retrace_extreme_px=99.75,
            elapsed_sec=20.0,
            ofi_pct=3.0,
            spread_bps=2.0,
        ).reason
    )
    # Default short flags fail closed (easy_to_borrow/shortable/ssr default False)
    assert (
        evaluate_suitable_timing_reentry(
            strategy_id="VIX_SPIKE_AND_CRUSH_REGIME_SURFER",
            exit_px=100.0,
            live_px=100.16,
            vwap_px=100.30,
            retrace_extreme_px=100.20,
            elapsed_sec=15.0,
            ofi_pct=-2.5,
            spread_bps=3.0,
            side="short",
        ).reason
        == "SHORT_ETB_OR_SSR_GATE_REFUSED"
    )

    # P1-5: paper-api.alpaca.markets allowed; unsanctioned / live / SaaS hosts rejected
    presets = _sample_six_uncapped_presets()
    ok_paper, errs_paper = validate_tv_preset_and_route_firewall(
        presets=presets, target_port=8799, target_host="paper-api.alpaca.markets"
    )
    assert ok_paper is True and errs_paper == []
    for bad_host in ("api.alpaca.markets", "signalstack.com", "broker-api.alpaca.markets"):
        ok_bh, errs_bh = validate_tv_preset_and_route_firewall(presets=presets, target_port=8799, target_host=bad_host)
        assert ok_bh is False and errs_bh

    # Sub-0.05% explicit stop cap never silently widened
    p_tight2 = compute_largecap_micro_trail_plan(
        entry_px="500.00",
        current_px="500.00",
        extreme_px="500.00",
        max_initial_stop_pct=0.02,
        adv_20d_usd=1e7,
        atr_1m_pct=1.0,
        spread_bps=30.0,
    )
    assert p_tight2.active_stop_px == Decimal("499.90")
    assert p_tight2.realized_risk_from_entry_bps <= 2.0 + 1e-6

    # P2-1 / P2-2 / P2-3: [6,14] bps preserved at 0.05% stop, sub-penny $1.0001 unarmed, 1.99x continuous equity cap
    p_tight = compute_largecap_micro_trail_plan(
        entry_px="500.00",
        current_px="500.00",
        extreme_px="500.00",
        max_initial_stop_pct=0.05,
        adv_20d_usd=1e9,
        atr_1m_pct=0.05,
        spread_bps=1.5,
    )
    assert 6.0 <= p_tight.target_trail_bps <= 14.0

    p_subpenny = compute_largecap_micro_trail_plan(
        entry_px="1.0001",
        current_px="1.0021",
        extreme_px="1.0021",
        adv_20d_usd=1e9,
        atr_1m_pct=0.05,
        spread_bps=1.5,
    )
    assert p_subpenny.gain_lock_armed is False
    assert p_subpenny.phase == "UNARMED_SUBTICK"

    p_lev = compute_largecap_micro_trail_plan(
        entry_px="100.00",
        current_px="100.00",
        extreme_px="100.00",
        position_leverage_x=1.99,
        max_initial_stop_pct=2.00,
    )
    assert p_lev.realized_risk_from_entry_bps * 1.99 <= 135.5
