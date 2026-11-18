"""Pre-Wall (`<= 2026-10-15`) Tight-Spread High-OFI Passive-Bid x Pure ADR-0022 Catastrophe Hold (`H090`).

Implements pre-registered Trial #90 (`H090_TIGHT_SPREAD_HIGH_OFI_PASSIVE_BID_ADR0022_EOD_HOLD`,
`spec_sha256 = c16d2a5794abd932869c16c9f158b3e0a61929aeb63a4b101aec98190434a5d1`, `t*(90) = 4.1735`):

Tests the synthesized microstructure hypothesis from `H085`–`H089`:
1. Restrict `hftbacktest::RiskAdverseQueueModel` passive L1 bid entries strictly to liquid tight-spread
   (`0 < entry_spread_bps <= 10.0`, `ADV_20d >= $20M`) symbols with strong positive order-flow imbalance
   (`ofi >= 0.25`), informed `F` ISO or BJZZ institutional sub-penny dark-pool participation, `T-1`
   `regsho_short_ratio >= 0.45`, and 90-day `S-3`/`424B*` dilution shielding (Glosten & Milgrom 1985).
2. Hold to `15:54` ET RTH close protected solely by the fixed `ADR-0022` `2.00%` (`200.0` bps)
   `ADVERSE_STOP_FIRST` catastrophe stop—eliminating the premature `45`–`120` bps intraday noise-trail
   ratchet stopouts observed in `H087`–`H089` (Kaminski & Lo 2014).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import numpy as np
import polars as pl
from ml4t.diagnostic.evaluation.stats import deflated_sharpe_ratio_from_statistics
from skfolio.model_selection import CombinatorialPurgedCV

from cc_sota_harness.compounding_pipeline import hlz_t_hurdle
from cc_sota_harness.gates import STUDY_WALL, check_study_wall
from cc_sota_harness.passive_bid_trail_prewall import (
    DILUTION_FORMS,
    EXIT_HALF_SPREAD_1X_BPS,
    NY_TZ,
    TICKET_NOTIONAL_USD,
    AdverseBar1m,
    H088SubperiodSummary,
    QuoteTickNs,
    TrailExitResult,
    _cvar95_bps,
    _date_clustered_mean_se_tstat,
    _extract_single_orb_passive_candidate,
    _sample_moments,
)
from cc_sota_harness.workstation_lane import resolve_prewall_lake_root, resolve_workstation_repo_dir

H090_HYPOTHESIS_ID = "H090_TIGHT_SPREAD_HIGH_OFI_PASSIVE_BID_ADR0022_EOD_HOLD"
H090_TRIAL_N = 90
H090_SPEC_SHA256 = "c16d2a5794abd932869c16c9f158b3e0a61929aeb63a4b101aec98190434a5d1"

H090_MAX_ENTRY_SPREAD_BPS = 10.0
H090_MIN_ADV_20D_USD = 20_000_000.0
H090_MIN_OFI = 0.25
ADR0022_CATASTROPHE_STOP_RATIO = 0.0200  # Exact 2.00% (200.0 bps) hard catastrophe cap


@dataclass(frozen=True, slots=True)
class H090PrewallResult:
    hypothesis_id: str
    spec_sha256: str
    evaluated_at_utc: str
    sample_min_date: str
    sample_max_date: str
    cumulative_trials_n: int
    required_hlz_t_hurdle: float
    tight_liquid_orb_events_total: int
    shielded_ignition_signals: int
    filled_events_count: int
    unfilled_runaway_count: int
    passive_fill_rate_pct: float
    distinct_dates: int
    mean_entry_spread_bps: float
    adverse_selection_bps: float
    cvar95_bps: float
    gross_excess_bps: float
    mean_exit_cost_1x_bps: float
    net_return_1x_bps: float
    net_return_2x_bps: float
    net_1x_without_best_day_bps: float
    t_stat_clustered_1x: float
    t_stat_clustered_2x: float
    daily_sharpe_native: float
    annualized_sharpe_1x: float
    dsr_probability: float
    deflated_sharpe_native: float
    cpcv_n_paths: int
    cpcv_median_oos_sharpe_annualized: float
    cpcv_positive_path_fraction: float
    exit_reason_counts: dict[str, int]
    subperiods: list[H088SubperiodSummary]
    passes_all_gates: bool


def replay_adr0022_catastrophe_eod_exit(
    *,
    entry_px: float,
    fill_ts_ns: int,
    post_fill_quotes: Sequence[QuoteTickNs],
    intraday_bars: Sequence[AdverseBar1m],
    fallback_close_px: float,
    exit_cost_1x_bps: float,
    catastrophe_stop_ratio: float = ADR0022_CATASTROPHE_STOP_RATIO,
) -> TrailExitResult:
    """Hold to 15:54 ET close protected solely by fixed ADR-0022 `<= 2.00%` `ADVERSE_STOP_FIRST` stop."""
    if (
        not (
            math.isfinite(entry_px)
            and math.isfinite(fallback_close_px)
            and math.isfinite(exit_cost_1x_bps)
            and math.isfinite(catastrophe_stop_ratio)
        )
        or entry_px <= 0.0
        or fallback_close_px <= 0.0
        or exit_cost_1x_bps < 0.0
        or not (0.0 < catastrophe_stop_ratio <= ADR0022_CATASTROPHE_STOP_RATIO)
    ):
        raise ValueError("Invalid replay_adr0022_catastrophe_eod_exit inputs")

    stop_px = entry_px * (1.0 - catastrophe_stop_ratio)
    last_ns_checked = fill_ts_ns

    for qt in post_fill_quotes:
        if qt.ts_ns <= fill_ts_ns or qt.bid_px <= 0.0:
            continue
        last_ns_checked = max(last_ns_checked, qt.ts_ns)
        if qt.bid_px <= stop_px + 1e-9:
            exit_px = min(qt.bid_px, stop_px)
            gross_bps = ((exit_px / entry_px) - 1.0) * 10_000.0
            return TrailExitResult(
                exit_reason="quote_adr0022_catastrophe_stop",
                exit_px=exit_px,
                gross_return_bps=gross_bps,
                net_return_1x_bps=gross_bps - exit_cost_1x_bps,
                net_return_2x_bps=gross_bps - 2.0 * exit_cost_1x_bps,
                gain_lock_armed=False,
            )

    last_bar_close = fallback_close_px
    for bar in intraday_bars:
        if bar.ts_ns <= last_ns_checked:
            continue
        last_bar_close = bar.close_px
        if bar.low_px <= stop_px + 1e-9:
            exit_px = min(bar.open_px, stop_px)
            gross_bps = ((exit_px / entry_px) - 1.0) * 10_000.0
            return TrailExitResult(
                exit_reason="bar_adr0022_catastrophe_stop",
                exit_px=exit_px,
                gross_return_bps=gross_bps,
                net_return_1x_bps=gross_bps - exit_cost_1x_bps,
                net_return_2x_bps=gross_bps - 2.0 * exit_cost_1x_bps,
                gain_lock_armed=False,
            )

    gross_bps = ((last_bar_close / entry_px) - 1.0) * 10_000.0
    return TrailExitResult(
        exit_reason="time_flatten_1554",
        exit_px=last_bar_close,
        gross_return_bps=gross_bps,
        net_return_1x_bps=gross_bps - exit_cost_1x_bps,
        net_return_2x_bps=gross_bps - 2.0 * exit_cost_1x_bps,
        gain_lock_armed=False,
    )


def evaluate_h090_prewall_panel(
    panel_df: pl.DataFrame,
    *,
    all_session_dates: Sequence[dt.date],
    cumulative_trials_n: int = H090_TRIAL_N,
) -> H090PrewallResult:
    """Evaluate pre-registered H090 metrics strictly `<= 2026-10-15`."""
    if panel_df.is_empty():
        raise ValueError("panel_df must not be empty")

    min_d: dt.date = panel_df.select(pl.col("trade_date").min()).item()
    max_d: dt.date = panel_df.select(pl.col("trade_date").max()).item()
    check_study_wall(min_d, stage="calibration")
    check_study_wall(max_d, stage="calibration")
    for sd in all_session_dates:
        check_study_wall(sd, stage="calibration")

    tight_liquid = panel_df.filter(
        (pl.col("prev_raw_close") >= 5.0)
        & (pl.col("adv_20d_usd") >= H090_MIN_ADV_20D_USD)
        & pl.col("sigma_20d").is_finite()
        & (pl.col("split_drift") < 1e-4)
        & (pl.col("entry_spread_bps") > 0.0)
        & (pl.col("entry_spread_bps") <= H090_MAX_ENTRY_SPREAD_BPS)
    )
    if tight_liquid.is_empty():
        raise ValueError("Tight-spread liquid pre-wall ORB panel is empty")

    exit_1x_base = EXIT_HALF_SPREAD_1X_BPS / 10_000.0
    enriched = tight_liquid.with_columns(
        [
            (
                pl.lit(exit_1x_base)
                + 0.10 * pl.col("sigma_20d") * (pl.lit(TICKET_NOTIONAL_USD) / pl.col("adv_20d_usd")).sqrt()
            ).alias("exit_cost_1x_ratio"),
            (
                (pl.col("ofi") >= H090_MIN_OFI)
                & ((pl.col("iso_f_buy_share") >= 0.15) | (pl.col("bjzz_inst_dark_share") >= 0.12))
                & (pl.col("regsho_short_ratio") >= 0.45)
            ).alias("tape_ignition_h090"),
        ]
    )

    shielded = enriched.filter(pl.col("tape_ignition_h090") & (~pl.col("recent_dilution_90d")))
    filled = shielded.filter(pl.col("passive_filled")).sort(["trade_date", "symbol"])
    unfilled = shielded.filter(~pl.col("passive_filled"))
    if filled.is_empty():
        raise ValueError("No filled H090 events in panel")

    fill_rate_pct = (100.0 * filled.height / shielded.height) if shielded.height > 0 else 0.0
    filled_mid_bps = (
        float(np.mean(np.asarray(filled["hold_close_from_mid_ret"].to_numpy(), dtype=np.float64))) * 10_000.0
    )
    unfilled_mid_bps = (
        float(np.mean(np.asarray(unfilled["hold_close_from_mid_ret"].to_numpy(), dtype=np.float64))) * 10_000.0
        if unfilled.height > 0
        else 0.0
    )
    adverse_sel_bps = filled_mid_bps - unfilled_mid_bps

    filled = filled.with_columns(
        [
            (pl.col("catastrophe_gross_ret") - pl.col("univ_orb_ret")).alias("gross_excess_ret"),
            (pl.col("catastrophe_gross_ret") - pl.col("univ_orb_ret") - pl.col("exit_cost_1x_ratio")).alias(
                "net_1x_ret"
            ),
            (pl.col("catastrophe_gross_ret") - pl.col("univ_orb_ret") - 2.0 * pl.col("exit_cost_1x_ratio")).alias(
                "net_2x_ret"
            ),
        ]
    )

    net_1x_bps_arr = np.asarray(filled["net_1x_ret"].to_numpy(), dtype=np.float64) * 10_000.0
    net_2x_bps_arr = np.asarray(filled["net_2x_ret"].to_numpy(), dtype=np.float64) * 10_000.0
    gross_bps_arr = np.asarray(filled["gross_excess_ret"].to_numpy(), dtype=np.float64) * 10_000.0
    cost_bps_arr = np.asarray(filled["exit_cost_1x_ratio"].to_numpy(), dtype=np.float64) * 10_000.0
    spr_arr = np.asarray(filled["entry_spread_bps"].to_numpy(), dtype=np.float64)
    date_groups = np.asarray(filled["trade_date"].cast(pl.String).to_numpy())

    mean_1x_bps, _, t_1x = _date_clustered_mean_se_tstat(net_1x_bps_arr, date_groups)
    mean_2x_bps, _, t_2x = _date_clustered_mean_se_tstat(net_2x_bps_arr, date_groups)
    cvar95 = _cvar95_bps(net_1x_bps_arr)

    by_day = filled.group_by("trade_date").agg(pl.col("net_1x_ret").mean().alias("cohort_net_1x")).sort("trade_date")
    best_day = by_day.sort("cohort_net_1x", descending=True).select("trade_date").head(1).item()
    without_best = filled.filter(pl.col("trade_date") != pl.lit(best_day))
    no_best_bps = (
        float(np.mean(np.asarray(without_best["net_1x_ret"].to_numpy(), dtype=np.float64))) * 10_000.0
        if without_best.height > 0
        else 0.0
    )

    sessions_df = pl.DataFrame({"trade_date": sorted(set(all_session_dates))})
    daily_rets = np.asarray(
        sessions_df.join(by_day, on="trade_date", how="left")
        .with_columns(pl.col("cohort_net_1x").fill_null(0.0))["cohort_net_1x"]
        .to_numpy(),
        dtype=np.float64,
    )

    def _native_sr(arr: np.ndarray) -> float:
        sd = float(np.std(arr, ddof=1)) if arr.size > 2 else 0.0
        return float(np.mean(arr) / sd) if sd > 1e-12 else 0.0

    n_days = int(daily_rets.size)
    sr_native = _native_sr(daily_rets)
    sr_ann = sr_native * math.sqrt(252.0)
    var_trials = max(1.0 / max(float(n_days), 1.0), 1e-4)
    skew, ex_kurt, ac1 = _sample_moments(daily_rets)
    dsr_res = deflated_sharpe_ratio_from_statistics(
        observed_sharpe=sr_native,
        n_samples=max(n_days, 10),
        n_trials=max(cumulative_trials_n, 1),
        variance_trials=var_trials,
        benchmark_sharpe=0.0,
        skewness=skew,
        excess_kurtosis=ex_kurt,
        autocorrelation=ac1,
        frequency="daily",
    )

    cpcv_sharpes: list[float] = []
    if n_days >= 60:
        cv = CombinatorialPurgedCV(n_folds=6, n_test_folds=2, purged_size=1, embargo_size=1)
        dummy_x = daily_rets.reshape(-1, 1)
        splits = list(cv.split(dummy_x))
        path_ids = cv.get_path_ids()
        n_paths = int(path_ids.max()) + 1
        for pid in range(n_paths):
            segs: list[np.ndarray] = []
            for s_idx, (train_idx, test_folds) in enumerate(splits):
                if train_idx.size == 0:
                    continue
                for fold_pos, fold_indices in enumerate(test_folds):
                    if int(path_ids[s_idx, fold_pos]) == pid:
                        segs.append(np.asarray(fold_indices, dtype=int))
            if segs:
                full_oos_idx = np.sort(np.concatenate(segs))
                cpcv_sharpes.append(_native_sr(daily_rets[full_oos_idx]) * math.sqrt(252.0))

    cpcv_median = float(np.median(cpcv_sharpes)) if cpcv_sharpes else 0.0
    cpcv_pos_frac = float(np.mean([s > 0.0 for s in cpcv_sharpes])) if cpcv_sharpes else 0.0

    exit_counts: dict[str, int] = {}
    if "exit_reason" in filled.columns:
        for row in filled.group_by("exit_reason").len().iter_rows(named=True):
            exit_counts[str(row["exit_reason"])] = int(row["len"])

    subperiods: list[H088SubperiodSummary] = []
    yr_df = (
        filled.with_columns(pl.col("trade_date").dt.year().alias("year"))
        .group_by("year")
        .agg(
            [
                pl.len().alias("events"),
                pl.col("trade_date").n_unique().alias("dates"),
                (pl.col("net_1x_ret").mean() * 10_000.0).alias("m1x"),
                (pl.col("net_2x_ret").mean() * 10_000.0).alias("m2x"),
            ]
        )
        .sort("year")
    )
    for row in yr_df.iter_rows(named=True):
        subperiods.append(
            H088SubperiodSummary(
                year=int(row["year"]),
                filled_events=int(row["events"]),
                distinct_dates=int(row["dates"]),
                mean_net_1x_bps=round(float(row["m1x"]), 3),
                mean_net_2x_bps=round(float(row["m2x"]), 3),
            )
        )

    t_hurdle = hlz_t_hurdle(cumulative_trials_n)
    distinct_dt_count = int(filled["trade_date"].n_unique())
    passes = (
        filled.height >= 200
        and distinct_dt_count >= 60
        and t_1x >= t_hurdle
        and float(dsr_res.probability) >= 0.95
        and cpcv_pos_frac >= 0.80
        and mean_1x_bps > 0.0
        and mean_2x_bps > 0.0
        and no_best_bps > 0.0
    )

    return H090PrewallResult(
        hypothesis_id=H090_HYPOTHESIS_ID,
        spec_sha256=H090_SPEC_SHA256,
        evaluated_at_utc=dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        sample_min_date=min_d.isoformat(),
        sample_max_date=max_d.isoformat(),
        cumulative_trials_n=cumulative_trials_n,
        required_hlz_t_hurdle=t_hurdle,
        tight_liquid_orb_events_total=tight_liquid.height,
        shielded_ignition_signals=shielded.height,
        filled_events_count=filled.height,
        unfilled_runaway_count=unfilled.height,
        passive_fill_rate_pct=round(fill_rate_pct, 2),
        distinct_dates=distinct_dt_count,
        mean_entry_spread_bps=round(float(np.mean(spr_arr)), 3),
        adverse_selection_bps=round(adverse_sel_bps, 3),
        cvar95_bps=round(cvar95, 3),
        gross_excess_bps=round(float(np.mean(gross_bps_arr)), 3),
        mean_exit_cost_1x_bps=round(float(np.mean(cost_bps_arr)), 3),
        net_return_1x_bps=round(mean_1x_bps, 3),
        net_return_2x_bps=round(mean_2x_bps, 3),
        net_1x_without_best_day_bps=round(no_best_bps, 3),
        t_stat_clustered_1x=round(t_1x, 4),
        t_stat_clustered_2x=round(t_2x, 4),
        daily_sharpe_native=round(sr_native, 5),
        annualized_sharpe_1x=round(sr_ann, 4),
        dsr_probability=round(float(dsr_res.probability), 5),
        deflated_sharpe_native=round(float(dsr_res.deflated_sharpe), 5),
        cpcv_n_paths=len(cpcv_sharpes),
        cpcv_median_oos_sharpe_annualized=round(cpcv_median, 4),
        cpcv_positive_path_fraction=round(cpcv_pos_frac, 4),
        exit_reason_counts=exit_counts,
        subperiods=subperiods,
        passes_all_gates=passes,
    )


def run_local_h090_prewall_study(
    *,
    years: tuple[int, ...] = (2024, 2025, 2026),
    docs_root: Path | None = None,
) -> H090PrewallResult:
    """Execute full pre-wall (`<= 2026-10-15`) H090 evaluation across Mac M5 Max, Noesis Win32, or Noesis-Carbon WSL2."""
    if docs_root is not None:
        u_root = docs_root / "trading-sota" / "data" / "private" / "universe"
        lake_root = docs_root / "market-data"
    else:
        lake_root = resolve_prewall_lake_root()
        u_cand = lake_root / "universe"
        u_root = (
            u_cand
            if u_cand.is_dir()
            else (resolve_workstation_repo_dir("trading-sota") / "data" / "private" / "universe")
        )
    sip_raw = lake_root / "alpaca-sip" / "raw"
    o_root = sip_raw / "published-orb"
    bars_root = sip_raw / "bars-1min"
    p_root = lake_root / "public" / "tables"

    wall_iso = STUDY_WALL.isoformat()
    sec_symbols = pl.read_parquet(p_root / "sec_symbols.parquet")
    sec_filings = pl.read_parquet(p_root / "sec_filings.parquet").filter(pl.col("filed").str.slice(0, 10) <= wall_iso)
    short_vol = pl.read_parquet(p_root / "short_volume.parquet").filter(pl.col("day").str.slice(0, 10) <= wall_iso)

    op_set = set(
        sec_symbols.filter((pl.col("entity_type") == "operating") & pl.col("symbol").str.contains(r"^[A-Z]{1,4}$"))[
            "symbol"
        ].to_list()
    )

    daily_frames: list[pl.DataFrame] = []
    for yr in years:
        raw_df = (
            pl.read_csv(u_root / str(yr) / "daily_raw.csv.gz", columns=["symbol", "ts_utc", "close", "volume"])
            .with_columns(pl.col("ts_utc").str.slice(0, 10).alias("day_str"))
            .filter((pl.col("day_str") <= wall_iso) & pl.col("symbol").is_in(op_set))
            .select(
                [
                    pl.col("symbol"),
                    pl.col("day_str").str.to_date().alias("trade_date"),
                    pl.col("close").cast(pl.Float64).alias("raw_close"),
                    pl.col("volume").cast(pl.Float64).alias("raw_volume"),
                ]
            )
        )
        spl_df = (
            pl.read_csv(u_root / str(yr) / "daily_split.csv.gz", columns=["symbol", "ts_utc", "close"])
            .with_columns(pl.col("ts_utc").str.slice(0, 10).alias("day_str"))
            .filter((pl.col("day_str") <= wall_iso) & pl.col("symbol").is_in(op_set))
            .select(
                [
                    pl.col("symbol"),
                    pl.col("day_str").str.to_date().alias("trade_date"),
                    pl.col("close").cast(pl.Float64).alias("split_close"),
                ]
            )
        )
        daily_frames.append(spl_df.join(raw_df, on=["symbol", "trade_date"], how="inner"))

    daily_df = (
        pl.concat(daily_frames, how="vertical")
        .unique(subset=["symbol", "trade_date"], keep="last")
        .sort(["symbol", "trade_date"])
        .with_columns(
            [
                (pl.col("raw_close") * pl.col("raw_volume")).alias("raw_dv"),
                (pl.col("split_close") / pl.col("split_close").shift(1).over("symbol") - 1.0).alias("ret_1d"),
                pl.col("raw_close").shift(1).over("symbol").alias("prev_raw_close"),
                pl.col("split_close").shift(1).over("symbol").alias("prev_split_close"),
                (pl.col("split_close") / pl.col("raw_close")).alias("adj_factor"),
            ]
        )
        .with_columns(
            [
                pl.col("raw_dv")
                .shift(1)
                .rolling_median(window_size=20, min_samples=20)
                .over("symbol")
                .alias("adv_20d_usd"),
                pl.col("ret_1d").shift(1).rolling_std(window_size=20, min_samples=20).over("symbol").alias("sigma_20d"),
                (((pl.col("prev_split_close") / pl.col("prev_raw_close")) / pl.col("adj_factor") - 1.0).abs()).alias(
                    "split_drift"
                ),
            ]
        )
    )

    work_items: list[tuple[str, dt.date, str, Path, Path]] = []
    trades_base = o_root / "trades"
    quotes_base = o_root / "quotes"
    for sym_dir in sorted(trades_base.iterdir()):
        if not sym_dir.is_dir() or sym_dir.name not in op_set:
            continue
        q_sym_dir = quotes_base / sym_dir.name
        if not q_sym_dir.is_dir():
            continue
        for tf in sorted(sym_dir.glob("*.parquet")):
            stem = tf.stem
            if len(stem) < 15 or stem[:10] > wall_iso:
                continue
            qf = q_sym_dir / tf.name
            if not qf.is_file():
                continue
            d_obj = dt.date.fromisoformat(stem[:10])
            check_study_wall(d_obj, stage="calibration")
            work_items.append((sym_dir.name, d_obj, stem[11:15], tf, qf))

    with ThreadPoolExecutor(max_workers=10) as pool:
        raw_candidates = [r for r in pool.map(_extract_single_orb_passive_candidate, work_items) if r is not None]

    quotes_by_key: dict[tuple[str, dt.date, str], list[QuoteTickNs]] = {}
    clean_rows: list[dict[str, object]] = []
    for item_dict in raw_candidates:
        key = (
            str(item_dict["symbol"]),
            cast(dt.date, item_dict["trade_date"]),
            str(item_dict["entry_hhmm"]),
        )
        quotes_by_key[key] = cast(list[QuoteTickNs], item_dict.pop("post_fill_quotes"))
        clean_rows.append(item_dict)

    orb_df = pl.DataFrame(clean_rows)
    dilution_pit = (
        sec_filings.filter(pl.col("form").is_in(DILUTION_FORMS))
        .join(sec_symbols.select(["cik", "symbol"]), on="cik", how="inner")
        .with_columns(pl.col("filed").str.slice(0, 10).str.to_date().alias("filed_date"))
        .select(["symbol", "filed_date"])
        .unique()
        .sort(["symbol", "filed_date"])
    )
    short_pit = (
        short_vol.with_columns(
            [
                pl.col("day").str.slice(0, 10).str.to_date().alias("sv_date"),
                (pl.col("short_volume").cast(pl.Float64) / pl.col("total_volume").cast(pl.Float64)).alias(
                    "regsho_short_ratio"
                ),
            ]
        )
        .filter(pl.col("total_volume") > 0)
        .select(["symbol", "sv_date", "regsho_short_ratio"])
        .unique(subset=["symbol", "sv_date"], keep="last")
        .sort(["symbol", "sv_date"])
    )

    panel = (
        orb_df.join(
            daily_df.select(
                ["symbol", "trade_date", "raw_close", "prev_raw_close", "adv_20d_usd", "sigma_20d", "split_drift"]
            ),
            on=["symbol", "trade_date"],
            how="inner",
        )
        .filter(
            (pl.col("prev_raw_close") >= 5.0)
            & (pl.col("adv_20d_usd") >= 5_000_000.0)
            & pl.col("sigma_20d").is_finite()
            & (pl.col("split_drift") < 1e-4)
            & (pl.col("entry_spread_bps") > 0.0)
            & (pl.col("entry_spread_bps") <= 35.0)
        )
        .with_columns(pl.col("trade_date").dt.offset_by("-1d").alias("prior_cal_date"))
        .sort(["symbol", "prior_cal_date"])
    )

    panel = panel.join_asof(
        dilution_pit,
        left_on="prior_cal_date",
        right_on="filed_date",
        by="symbol",
        strategy="backward",
        check_sortedness=False,
    ).with_columns(
        (
            pl.col("filed_date").is_not_null() & ((pl.col("trade_date") - pl.col("filed_date")).dt.total_days() <= 90)
        ).alias("recent_dilution_90d")
    )
    panel = panel.join_asof(
        short_pit,
        left_on="prior_cal_date",
        right_on="sv_date",
        by="symbol",
        strategy="backward",
        check_sortedness=False,
    ).with_columns(
        [
            pl.col("regsho_short_ratio").fill_null(0.0),
            (pl.col("raw_close") / pl.col("mid_entry") - 1.0).alias("hold_close_from_mid_ret"),
        ]
    )
    # Universe ORB benchmark computed across full liquid ORB cross-section on date t before tight-spread selection
    panel = panel.with_columns(pl.col("hold_close_from_mid_ret").mean().over("trade_date").alias("univ_orb_ret"))

    ign_mask = (
        (pl.col("adv_20d_usd") >= H090_MIN_ADV_20D_USD)
        & (pl.col("entry_spread_bps") <= H090_MAX_ENTRY_SPREAD_BPS)
        & (pl.col("ofi") >= H090_MIN_OFI)
        & ((pl.col("iso_f_buy_share") >= 0.15) | (pl.col("bjzz_inst_dark_share") >= 0.12))
        & (pl.col("regsho_short_ratio") >= 0.45)
        & (~pl.col("recent_dilution_90d"))
        & pl.col("passive_filled")
    )
    filled_targets = panel.filter(ign_mask)
    syms_by_date: dict[dt.date, set[str]] = {}
    for sym_v, dt_v in zip(filled_targets["symbol"].to_list(), filled_targets["trade_date"].to_list(), strict=False):
        syms_by_date.setdefault(dt_v, set()).add(str(sym_v))

    def _load_day_bars(
        item: tuple[dt.date, set[str]],
    ) -> tuple[dt.date, dict[str, list[tuple[int, float, float, float, float]]]]:
        d_val, sym_set = item
        day_dir = bars_root / d_val.isoformat()
        if not day_dir.is_dir():
            return d_val, {}
        rth_open_ns = int(dt.datetime.combine(d_val, dt.time(9, 30, 0), tzinfo=NY_TZ).timestamp() * 1_000_000_000)
        flatten_ns = int(dt.datetime.combine(d_val, dt.time(15, 54, 0), tzinfo=NY_TZ).timestamp() * 1_000_000_000)
        df_b = (
            pl.scan_parquet(str(day_dir / "*.parquet"))
            .filter(
                pl.col("symbol").is_in(list(sym_set))
                & (pl.col("t_ns") >= rth_open_ns)
                & (pl.col("t_ns") <= flatten_ns)
                & (pl.col("l") > 0.0)
            )
            .select(["symbol", "t_ns", "o", "h", "l", "c"])
            .collect()
            .sort(["symbol", "t_ns"])
        )
        grouped: dict[str, list[tuple[int, float, float, float, float]]] = {}
        for s_n, t_n, o_p, h_p, l_p, c_p in zip(
            df_b["symbol"].to_list(),
            df_b["t_ns"].to_list(),
            df_b["o"].to_list(),
            df_b["h"].to_list(),
            df_b["l"].to_list(),
            df_b["c"].to_list(),
            strict=False,
        ):
            grouped.setdefault(str(s_n), []).append((int(t_n), float(o_p), float(h_p), float(l_p), float(c_p)))
        return d_val, grouped

    bars_lookup: dict[tuple[str, dt.date], list[tuple[int, float, float, float, float]]] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for d_val, sym_map in pool.map(_load_day_bars, list(syms_by_date.items())):
            for sym_k, bar_list in sym_map.items():
                bars_lookup[(sym_k, d_val)] = bar_list

    cat_gross_col: list[float] = []
    exit_reason_col: list[str] = []

    for row in panel.iter_rows(named=True):
        key_b = (str(row["symbol"]), row["trade_date"])
        if not row["passive_filled"] or key_b not in bars_lookup:
            cat_gross_col.append(0.0)
            exit_reason_col.append("unfilled_or_filtered")
            continue

        key_q = (str(row["symbol"]), row["trade_date"], str(row["entry_hhmm"]))
        day_bars = bars_lookup.get(key_b, [])
        fill_ts_v = int(row["fill_ts_ns"])
        rem_quotes_v = quotes_by_key.get(key_q, [])
        handoff_ns = max((qt.ts_ns for qt in rem_quotes_v), default=fill_ts_v)
        post_bars = [
            AdverseBar1m(ts_ns=t_n + 60_000_000_000, open_px=o_p, high_px=h_p, low_px=l_p, close_px=c_p)
            for (t_n, o_p, h_p, l_p, c_p) in day_bars
            if t_n >= handoff_ns
        ]
        cost_1x_bps = (
            EXIT_HALF_SPREAD_1X_BPS
            + 0.10 * float(row["sigma_20d"]) * math.sqrt(TICKET_NOTIONAL_USD / float(row["adv_20d_usd"])) * 10_000.0
        )
        res_exit = replay_adr0022_catastrophe_eod_exit(
            entry_px=float(row["bp_entry"]),
            fill_ts_ns=fill_ts_v,
            post_fill_quotes=rem_quotes_v,
            intraday_bars=post_bars,
            fallback_close_px=float(row["raw_close"]),
            exit_cost_1x_bps=cost_1x_bps,
        )
        cat_gross_col.append(res_exit.gross_return_bps / 10_000.0)
        exit_reason_col.append(res_exit.exit_reason)

    panel = panel.with_columns(
        [
            pl.Series("catastrophe_gross_ret", cat_gross_col, dtype=pl.Float64),
            pl.Series("exit_reason", exit_reason_col, dtype=pl.String),
        ]
    )
    all_sessions = daily_df.select("trade_date").unique().sort("trade_date")["trade_date"].to_list()
    return evaluate_h090_prewall_panel(panel, all_session_dates=all_sessions, cumulative_trials_n=H090_TRIAL_N)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pre-registered H090 pre-wall study (<=2026-10-15)")
    parser.add_argument("--out-json", type=str, default="")
    args = parser.parse_args()

    res = run_local_h090_prewall_study()
    payload = json.dumps(asdict(res), indent=2)
    if args.out_json:
        out_p = Path(args.out_json).expanduser().resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
