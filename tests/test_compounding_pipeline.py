"""Unit and Hypothesis property tests for the 5-stage strategy compounding pipeline."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cc_sota_harness.compounding_pipeline import (
    BrokerTargetConfig,
    DataFeedPITContract,
    LifecycleStage,
    StrategyLifecycleRecord,
    calibrate_protective_trail_pct,
    compute_ex_ante_mde_bps,
    empirical_bayes_shrink_edge,
    evaluate_strategy_promotion,
    hlz_t_hurdle,
    validate_broker_target,
    validate_compounding_manifest,
    validate_legacy_harvest_manifest,
)
from cc_sota_harness.gates import MAX_PROTECTIVE_STOP_PCT, STUDY_WALL, OrderIntent, check_paper_order_intent
from cc_sota_harness.upstream_execution_parity import HFTBACKTEST_PIN, NAUTILUS_PIN


def _valid_alpaca_broker() -> BrokerTargetConfig:
    return BrokerTargetConfig(
        broker="alpaca_paper",
        venue_prefix="PA",
        endpoint_or_host="paper-api.alpaca.markets",
        port=None,
        max_rate_per_min=200,
        entry_rate_cap_per_min=180,
        protective_stop_pct=0.0195,
        rth_contingency="OTO",
        extended_session_protection="awake_limit_guardian_24x5",
    )


def _valid_ibkr_broker() -> BrokerTargetConfig:
    return BrokerTargetConfig(
        broker="ibkr_paper",
        venue_prefix="DU",
        endpoint_or_host="127.0.0.1",
        port=4002,
        max_rate_per_min=3000,
        entry_rate_cap_per_min=2700,
        protective_stop_pct=0.0195,
        rth_contingency="bracket_stop_limit",
        extended_session_protection="outside_rth_stop_limit",
    )


def _sample_record(target_stage: LifecycleStage = LifecycleStage.COMPOUNDING_FINETUNE) -> StrategyLifecycleRecord:
    return StrategyLifecycleRecord(
        strategy_id="SYNTHETIC_STAGE5_WITNESS",
        trial_n=83,
        spec_sha256="a" * 64,
        target_stage=target_stage,
        nautilus_pin=NAUTILUS_PIN,
        hftbacktest_pin=HFTBACKTEST_PIN,
        queue_model="RiskAdverseQueueModel",
        calibration_max_date=STUDY_WALL,
        events_count=640,
        distinct_dates=190,
        cpcv_folds=6,
        cpcv_test_folds=2,
        cpcv_positive_share=0.9333,
        dsr_probability=0.985,
        t_stat_clustered=4.42,
        net_return_1x_bps=24.5,
        net_return_2x_bps=12.8,
        verified_model_families=("anthropic", "openai", "google"),
        open_p0_p1_defects=0,
        brokers=(_valid_alpaca_broker(), _valid_ibkr_broker()),
        forward_shadow_start=dt.date(2026, 10, 16),
        eb_prior_mean_bps=12.8,
        eb_prior_std_bps=4.0,
        eb_obs_mean_bps=18.0,
        eb_obs_se_bps=6.0,
        lesson_recorded=True,
    )


def test_hlz_t_hurdle_matches_sota_bus_exact_values() -> None:
    assert hlz_t_hurdle(1) == 3.0
    assert hlz_t_hurdle(79) == 4.1437
    assert hlz_t_hurdle(83) == 4.155
    with pytest.raises(ValueError, match="positive integer"):
        hlz_t_hurdle(0)
    with pytest.raises(ValueError, match="positive integer"):
        hlz_t_hurdle(True)  # type: ignore[arg-type]


@given(
    n1=st.integers(min_value=1, max_value=5000),
    delta=st.integers(min_value=1, max_value=5000),
)
def test_property_hlz_hurdle_monotonic_in_trials(n1: int, delta: int) -> None:
    assert hlz_t_hurdle(n1 + delta) >= hlz_t_hurdle(n1)


@given(
    prior_mean=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    prior_std=st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False),
    obs_mean=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    obs_se=st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_property_empirical_bayes_convex_shrinkage(
    prior_mean: float,
    prior_std: float,
    obs_mean: float,
    obs_se: float,
) -> None:
    post, weight = empirical_bayes_shrink_edge(
        prior_mean_bps=prior_mean,
        prior_std_bps=prior_std,
        obs_mean_bps=obs_mean,
        obs_se_bps=obs_se,
    )
    lo, hi = min(prior_mean, obs_mean), max(prior_mean, obs_mean)
    assert 0.0 < weight < 1.0
    assert lo - 1e-9 <= post <= hi + 1e-9


@given(
    bar_range_bps=st.floats(min_value=1.0, max_value=2000.0, allow_nan=False, allow_infinity=False),
    mult=st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False),
)
def test_property_calibrated_trail_never_breaches_adr0022(bar_range_bps: float, mult: float) -> None:
    stop_pct = calibrate_protective_trail_pct(
        prewall_median_bar_range_bps=bar_range_bps,
        range_multiplier=mult,
    )
    assert 0.0035 <= stop_pct <= MAX_PROTECTIVE_STOP_PCT


def test_full_stage0_to_stage5_promotion_and_rejection_gates() -> None:
    verdict = evaluate_strategy_promotion(_sample_record())
    assert verdict.approved is True
    assert verdict.highest_cleared_stage == LifecycleStage.COMPOUNDING_FINETUNE
    assert verdict.eb_posterior_mean_bps is not None and verdict.eb_posterior_mean_bps > 12.8

    # Post-wall leakage must fail Stage 2
    leaked = replace(_sample_record(), calibration_max_date=dt.date(2026, 10, 16))
    v_leak = evaluate_strategy_promotion(leaked)
    assert v_leak.approved is False
    assert v_leak.highest_cleared_stage == LifecycleStage.SIM_QUEUE_PARITY

    # Single-family review must fail Stage 3
    mono_family = replace(_sample_record(), verified_model_families=("anthropic",))
    v_mono = evaluate_strategy_promotion(mono_family)
    assert v_mono.approved is False
    assert v_mono.highest_cleared_stage == LifecycleStage.PREWALL_BACKTEST


def test_live_capital_brokers_hard_refused() -> None:
    for bad_cfg in (
        replace(_valid_alpaca_broker(), broker="alpaca_live"),
        replace(_valid_alpaca_broker(), endpoint_or_host="api.alpaca.markets"),
        replace(_valid_alpaca_broker(), venue_prefix="U1"),
        replace(_valid_ibkr_broker(), port=4001),
        replace(_valid_ibkr_broker(), port=7496),
    ):
        with pytest.raises(PermissionError, match="hard-refused"):
            validate_broker_target(bad_cfg)

    with pytest.raises(ValueError, match="ADR-0022"):
        validate_broker_target(replace(_valid_alpaca_broker(), protective_stop_pct=0.0201))


def test_repo_strategy_compounding_manifest_validates_zero_errors() -> None:
    manifest, errors = validate_compounding_manifest()
    assert errors == []
    assert manifest["githubOrganization"]["name"] == "native-agent-stack"
    assert len(manifest["paperBrokerTargets"]) == 2
    assert len(manifest["empiricalTrialsArchive"]) == 2


@given(
    sigma_bps=st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    days=st.integers(min_value=10, max_value=1000),
    extra_days=st.integers(min_value=1, max_value=1000),
    trial_n=st.integers(min_value=1, max_value=500),
)
def test_property_ex_ante_mde_shrinks_with_sample_and_grows_with_trials(
    sigma_bps: float,
    days: int,
    extra_days: int,
    trial_n: int,
) -> None:
    mde1 = compute_ex_ante_mde_bps(fit_daily_sigma_bps=sigma_bps, held_out_days=days, trial_n=trial_n)
    mde_more_days = compute_ex_ante_mde_bps(
        fit_daily_sigma_bps=sigma_bps,
        held_out_days=days + extra_days,
        trial_n=trial_n,
    )
    mde_more_trials = compute_ex_ante_mde_bps(
        fit_daily_sigma_bps=sigma_bps,
        held_out_days=days,
        trial_n=trial_n + 10,
    )
    assert mde1 > mde_more_days > 0.0
    assert mde_more_trials >= mde1


def test_legacy_harvest_manifest_validates_all_47_superseded_repos() -> None:
    harvest, errors = validate_legacy_harvest_manifest()
    assert errors == []
    assert len(harvest["harvestedRepositories"]) == 47
    assert len(harvest["harvestedInvariants"]) == 6


def test_ao_remediation_vendor_allowlist_pit_contract_and_ibkr_reserve() -> None:
    # 1. Wrapper pseudo-vendor rejected in Stage 3 even when 3 strings are passed
    pseudo = replace(
        _sample_record(),
        verified_model_families=("anthropic", "google", "multi-router"),
    )
    v_pseudo = evaluate_strategy_promotion(pseudo)
    assert v_pseudo.approved is False
    assert v_pseudo.highest_cleared_stage == LifecycleStage.PREWALL_BACKTEST

    # 2. FINRA Rule 4560 short-interest dissemination lookahead (< 8 bdays) rejected in Stage 2
    bad_pit = replace(
        _sample_record(),
        pit_contract=DataFeedPITContract(finra_short_interest_lag_bdays=0),
    )
    v_pit = evaluate_strategy_promotion(bad_pit)
    assert v_pit.approved is False
    assert v_pit.highest_cleared_stage == LifecycleStage.SIM_QUEUE_PARITY

    # 3. Non-loopback IBKR host hard-refused and entry cap > 2700 rejected
    with pytest.raises(PermissionError, match="hard-refused"):
        validate_broker_target(replace(_valid_ibkr_broker(), endpoint_or_host="10.0.0.5"))
    with pytest.raises(ValueError, match="300 msg/min"):
        validate_broker_target(replace(_valid_ibkr_broker(), entry_rate_cap_per_min=2850))

    # 4. OrderIntent on DU reserves 300 msg/min for protective exits (2700 entry cap / 3000 exit cap)
    base_du = OrderIntent(
        venue_prefix="DU",
        symbol="NVDA",
        side="buy",
        entry_price=100.0,
        stop_price=98.5,
        session="overnight",
        has_broker_oto_stop=True,
        has_awake_limit_exit=False,
        requests_used_last_min=2700,
        is_protective_exit=False,
    )
    with pytest.raises(RuntimeError, match="rate-budget exceeded"):
        check_paper_order_intent(base_du)
    check_paper_order_intent(replace(base_du, is_protective_exit=True))
