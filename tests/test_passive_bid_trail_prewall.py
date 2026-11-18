"""Unit, dimensional, and Hypothesis property tests for H088 Passive-Bid x Variance-Compressing Trail."""

from __future__ import annotations

import datetime as dt
import math

import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cc_sota_harness.passive_bid_trail_prewall import (
    H088_HYPOTHESIS_ID,
    H088_SPEC_SHA256,
    H088_TRIAL_N,
    AdverseBar1m,
    QuoteTickNs,
    TradePrintNs,
    compute_h088_trail_ratio,
    evaluate_h088_prewall_panel,
    replay_adverse_stop_first_exit,
    simulate_passive_bid_orb_fill,
)


def test_cta_utp_round_lot_bs_scaling_blocks_premature_fill() -> None:
    """CTA/UTP quote bs=2.0 means 200 shares (not 2 shares); a 50-share print at bid must NOT deplete queue."""
    trades = (
        TradePrintNs(ts_ns=1_000, price_px=10.00, size_shares=50.0),
        TradePrintNs(ts_ns=2_000, price_px=10.00, size_shares=120.0),
    )
    quotes = (QuoteTickNs(ts_ns=500, bid_px=10.00, bid_lots=2.0, ask_px=10.02, ask_lots=2.0),)
    unfilled = simulate_passive_bid_orb_fill(
        limit_bid_px=10.00,
        initial_bid_lots=2.0,
        order_qty_shares=100.0,
        trades=trades,
        quotes=quotes,
    )
    assert not unfilled.filled
    assert unfilled.fill_reason == "expired_unfilled"

    # Adding another 150 shares (total 320 >= 200 front + 100 order) depletes RiskAdverseQueueModel queue
    trades_full = trades + (TradePrintNs(ts_ns=3_000, price_px=10.00, size_shares=150.0),)
    filled = simulate_passive_bid_orb_fill(
        limit_bid_px=10.00,
        initial_bid_lots=2.0,
        order_qty_shares=100.0,
        trades=trades_full,
        quotes=quotes,
    )
    assert filled.filled
    assert filled.fill_px == pytest.approx(10.00)
    assert filled.fill_ts_ns == 3_000
    assert filled.fill_reason == "queue_depleted"


def test_adverse_stop_first_checks_low_before_high_ratchet() -> None:
    """On an ambiguous 1m bar that hits BOTH low<=stop and a new high, ADVERSE_STOP_FIRST must stop out first."""
    entry_px = 100.00
    trail_ratio = 0.0100  # 100 bps => initial stop = 99.00
    # Ambiguous bar opens at 100.00, spikes high=105.00 (+500 bps) AND drops low=98.80 (<= 99.00)
    bars = (AdverseBar1m(ts_ns=10_000_000_000, open_px=100.0, high_px=105.0, low_px=98.80, close_px=104.5),)
    out = replay_adverse_stop_first_exit(
        entry_px=entry_px,
        fill_ts_ns=1_000_000_000,
        trail_ratio=trail_ratio,
        post_fill_quotes=(),
        intraday_bars=bars,
        fallback_close_px=104.5,
        exit_cost_1x_bps=6.0,
    )
    assert out.exit_reason == "bar_adverse_stop"
    assert out.exit_px == pytest.approx(99.00)
    assert out.gross_return_bps == pytest.approx(-100.0)
    assert out.net_return_1x_bps == pytest.approx(-106.0)
    assert out.net_return_2x_bps == pytest.approx(-112.0)


def test_gain_lock_ratchet_captures_mfe_before_pullback() -> None:
    """Clean upward bar ratchets Gain-Lock (+60 bps arm, 65% MFE retention) before subsequent pullback bar."""
    entry_px = 100.00
    trail_ratio = 0.0120  # 120 bps initial stop (98.80)
    bars = (
        AdverseBar1m(ts_ns=10_000_000_000, open_px=100.0, high_px=102.00, low_px=99.90, close_px=101.80),
        AdverseBar1m(ts_ns=70_000_000_000, open_px=101.70, high_px=101.75, low_px=100.50, close_px=100.60),
    )
    out = replay_adverse_stop_first_exit(
        entry_px=entry_px,
        fill_ts_ns=1_000_000_000,
        trail_ratio=trail_ratio,
        post_fill_quotes=(),
        intraday_bars=bars,
        fallback_close_px=100.60,
        exit_cost_1x_bps=5.0,
    )
    assert out.exit_reason == "bar_gain_lock_or_trail"
    assert out.exit_px > entry_px
    assert out.gross_return_bps > 100.0


def test_postwall_and_nonfinite_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="finite"):
        compute_h088_trail_ratio(float("nan"))
    with pytest.raises(ValueError, match="study-wall"):
        df = pl.DataFrame(
            {
                "symbol": ["AAPL"],
                "trade_date": [dt.date(2026, 10, 16)],
                "prev_raw_close": [200.0],
                "adv_20d_usd": [50_000_000.0],
                "sigma_20d": [0.02],
                "split_drift": [0.0],
                "entry_spread_bps": [10.0],
                "ofi": [0.25],
                "iso_f_buy_share": [0.20],
                "bjzz_inst_dark_share": [0.15],
                "regsho_short_ratio": [0.50],
                "recent_dilution_90d": [False],
                "passive_filled": [True],
                "trail_gross_ret": [0.005],
                "hold_close_from_mid_ret": [0.004],
                "univ_orb_ret": [0.001],
            }
        )
        evaluate_h088_prewall_panel(df, all_session_dates=[dt.date(2026, 10, 16)])


@given(
    entry_px=st.floats(min_value=5.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    pre_range_bps=st.floats(min_value=10.0, max_value=600.0, allow_nan=False, allow_infinity=False),
    cost_1x_bps=st.floats(min_value=1.0, max_value=25.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=60)
def test_property_trail_bounds_and_cost_monotonicity(
    entry_px: float,
    pre_range_bps: float,
    cost_1x_bps: float,
) -> None:
    trail_ratio = compute_h088_trail_ratio(pre_range_bps)
    assert math.isfinite(trail_ratio)
    assert 0.0045 <= trail_ratio <= 0.0180

    out = replay_adverse_stop_first_exit(
        entry_px=entry_px,
        fill_ts_ns=1_000,
        trail_ratio=trail_ratio,
        post_fill_quotes=(
            QuoteTickNs(ts_ns=2_000, bid_px=entry_px * 1.008, bid_lots=3.0, ask_px=entry_px * 1.009, ask_lots=3.0),
        ),
        intraday_bars=(),
        fallback_close_px=entry_px * 1.007,
        exit_cost_1x_bps=cost_1x_bps,
    )
    assert out.net_return_2x_bps < out.net_return_1x_bps < out.gross_return_bps
    assert out.gross_return_bps >= -(trail_ratio * 10_000.0 + 1e-6)


def test_h088_preregistration_constants_and_synthetic_panel() -> None:
    assert H088_HYPOTHESIS_ID == "H088_PASSIVE_BID_X_VARIANCE_COMPRESSING_DYNAMIC_TRAIL"
    assert H088_TRIAL_N == 88
    assert len(H088_SPEC_SHA256) == 64

    base_d = dt.date(2025, 1, 2)
    rows = []
    sessions = []
    for i in range(70):
        d = base_d + dt.timedelta(days=i)
        sessions.append(d)
        for s_idx, sym in enumerate(("NVDA", "AMD", "AVGO", "SMCI")):
            filled = (i + s_idx) % 5 != 0
            rows.append(
                {
                    "symbol": sym,
                    "trade_date": d,
                    "prev_raw_close": 50.0,
                    "adv_20d_usd": 25_000_000.0,
                    "sigma_20d": 0.025,
                    "split_drift": 0.0,
                    "entry_spread_bps": 12.0,
                    "ofi": 0.22,
                    "iso_f_buy_share": 0.20,
                    "bjzz_inst_dark_share": 0.14,
                    "regsho_short_ratio": 0.48,
                    "recent_dilution_90d": False,
                    "passive_filled": filled,
                    "trail_gross_ret": 0.0045 if filled else 0.0,
                    "hold_close_from_mid_ret": 0.0030 if filled else 0.0065,
                    "univ_orb_ret": 0.0005,
                }
            )
    panel_df = pl.DataFrame(rows)
    res = evaluate_h088_prewall_panel(panel_df, all_session_dates=sessions)
    assert res.cumulative_trials_n == 88
    assert res.required_hlz_t_hurdle == pytest.approx(4.1683)
    assert res.filled_events_count > 200
    assert res.distinct_dates == 70
    assert res.cpcv_n_paths == 5
    assert res.adverse_selection_bps < 0.0
