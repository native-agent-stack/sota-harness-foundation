"""5-Stage Strategy Promotion, Empirical-Bayes Fine-Tuning & Paper Broker Routing Engine.

Codifies the governed lifecycle from pre-registered hypothesis -> upstream queue-fill
simulation -> pre-wall (<= 2026-10-15) CPCV/DSR/2x-impact backtest -> multi-model
adversarial falsification -> autonomous Alpaca/IBKR Paper execution -> Empirical-Bayes
factor fine-tuning and SkillOpt lesson compounding.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import pathlib
import re
import statistics
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum
from typing import Any

from cc_sota_harness.gates import (
    ALPACA_PAPER_MAX_RPM,
    IBKR_PAPER_MAX_MPM,
    MAX_PROTECTIVE_STOP_DEC,
    MAX_PROTECTIVE_STOP_PCT,
    PROTECTIVE_EXIT_RESERVE_RPM,
    STUDY_WALL,
)
from cc_sota_harness.upstream_execution_parity import HFTBACKTEST_PIN, NAUTILUS_PIN

HLZ_BASE_ONE_SIDED_P = 0.00135
_STD_NORM = statistics.NormalDist(0.0, 1.0)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_MANIFEST_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "config" / "strategy-compounding-manifest.json"
)
DEFAULT_LEGACY_HARVEST_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "config" / "legacy-harvest-manifest.json"
)
_SHA1_40_RE = re.compile(r"^[0-9a-f]{40}$")


class LifecycleStage(StrEnum):
    HYPOTHESIS = "0_hypothesis_prereg"
    SIM_QUEUE_PARITY = "1_sim_queue_parity"
    PREWALL_BACKTEST = "2_prewall_backtest"
    MULTIMODEL_FALSIFICATION = "3_multimodel_falsification"
    PAPER_BROKER_EXECUTION = "4_paper_broker_execution"
    COMPOUNDING_FINETUNE = "5_compounding_finetune"


STAGE_ORDER: tuple[LifecycleStage, ...] = (
    LifecycleStage.HYPOTHESIS,
    LifecycleStage.SIM_QUEUE_PARITY,
    LifecycleStage.PREWALL_BACKTEST,
    LifecycleStage.MULTIMODEL_FALSIFICATION,
    LifecycleStage.PAPER_BROKER_EXECUTION,
    LifecycleStage.COMPOUNDING_FINETUNE,
)


def hlz_t_hurdle(trial_n: int) -> float:
    """Compute Harvey-Liu-Zhu dynamic multiple-testing hurdle t*(N) matching sota-bus."""
    if isinstance(trial_n, bool) or not isinstance(trial_n, int) or trial_n < 1:
        raise ValueError(f"trial_n must be a positive integer >= 1, got {trial_n!r}")
    p_target = HLZ_BASE_ONE_SIDED_P / float(trial_n)
    return round(float(_STD_NORM.inv_cdf(1.0 - p_target)), 4)


def compute_ex_ante_mde_bps(
    *,
    fit_daily_sigma_bps: float,
    held_out_days: int,
    trial_n: int,
) -> float:
    """Compute ex-ante Minimum Detectable Effect (bps/day) before reading OOS data.

    Harvested from ``edge/CLAUDE.md`` & ``edge/LEARNED.md`` (Lesson 6): if no plausible
    post-cost edge exceeds ``t*(N) * sigma_fit / sqrt(held_out_days)``, do not burn
    held-out degrees of freedom.
    """
    if isinstance(fit_daily_sigma_bps, bool) or not math.isfinite(fit_daily_sigma_bps) or fit_daily_sigma_bps <= 0.0:
        raise ValueError(f"fit_daily_sigma_bps must be finite and > 0, got {fit_daily_sigma_bps!r}")
    if isinstance(held_out_days, bool) or not isinstance(held_out_days, int) or held_out_days < 1:
        raise ValueError(f"held_out_days must be an integer >= 1, got {held_out_days!r}")
    t_star = hlz_t_hurdle(trial_n)
    return (t_star * fit_daily_sigma_bps) / math.sqrt(float(held_out_days))


def empirical_bayes_shrink_edge(
    *,
    prior_mean_bps: float,
    prior_std_bps: float,
    obs_mean_bps: float,
    obs_se_bps: float,
) -> tuple[float, float]:
    """Shrink noisy forward paper observations toward the pre-wall prior (Gaussian EB).

    Returns ``(posterior_mean_bps, obs_weight)`` with ``0.0 < obs_weight < 1.0``.
    """
    for name, val in (
        ("prior_mean_bps", prior_mean_bps),
        ("prior_std_bps", prior_std_bps),
        ("obs_mean_bps", obs_mean_bps),
        ("obs_se_bps", obs_se_bps),
    ):
        if isinstance(val, bool) or not math.isfinite(val):
            raise ValueError(f"{name} must be a finite number, got {val!r}")
    if prior_std_bps <= 0.0:
        raise ValueError(f"prior_std_bps must be > 0, got {prior_std_bps}")
    if obs_se_bps <= 0.0:
        raise ValueError(f"obs_se_bps must be > 0, got {obs_se_bps}")

    ratio = obs_se_bps / prior_std_bps
    obs_weight = 1.0 / (1.0 + ratio * ratio)
    posterior_mean = prior_mean_bps + obs_weight * (obs_mean_bps - prior_mean_bps)
    return posterior_mean, obs_weight


def calibrate_protective_trail_pct(
    *,
    prewall_median_bar_range_bps: float,
    range_multiplier: float = 1.25,
    min_stop_pct: float = 0.0035,
) -> float:
    """Calibrate protective stop/trail width from pre-wall range while enforcing <= 2.00%."""
    for name, val in (
        ("prewall_median_bar_range_bps", prewall_median_bar_range_bps),
        ("range_multiplier", range_multiplier),
        ("min_stop_pct", min_stop_pct),
    ):
        if isinstance(val, bool) or not math.isfinite(val):
            raise ValueError(f"{name} must be finite, got {val!r}")
    if prewall_median_bar_range_bps <= 0.0 or range_multiplier <= 0.0:
        raise ValueError("prewall_median_bar_range_bps and range_multiplier must be > 0")
    if min_stop_pct <= 0.0 or Decimal(str(min_stop_pct)) > MAX_PROTECTIVE_STOP_DEC:
        raise ValueError(f"min_stop_pct must be in (0, {MAX_PROTECTIVE_STOP_PCT}], got {min_stop_pct}")

    raw_dec = (
        Decimal(str(prewall_median_bar_range_bps)) * Decimal(str(range_multiplier))
    ) / Decimal("10000")
    floored = raw_dec.quantize(Decimal("0.0001"), rounding=ROUND_FLOOR)
    min_dec = Decimal(str(min_stop_pct)).quantize(Decimal("0.0001"), rounding=ROUND_FLOOR)
    clamped = min(MAX_PROTECTIVE_STOP_DEC, max(min_dec, floored))
    return float(clamped)


@dataclass(frozen=True, slots=True)
class BrokerTargetConfig:
    broker: str
    venue_prefix: str
    endpoint_or_host: str
    port: int | None
    max_rate_per_min: int
    entry_rate_cap_per_min: int
    protective_stop_pct: float
    rth_contingency: str
    extended_session_protection: str


def validate_broker_target(cfg: BrokerTargetConfig) -> None:
    """Enforce paper-only broker routing, rate pacing, and ADR-0022 <= 2.00% stops."""
    if cfg.broker not in ("alpaca_paper", "ibkr_paper"):
        raise PermissionError(
            f"Broker target {cfg.broker!r} is hard-refused; only 'alpaca_paper' and 'ibkr_paper' are permitted"
        )
    if "api.alpaca.markets" in cfg.endpoint_or_host and "paper-api.alpaca.markets" not in cfg.endpoint_or_host:
        raise PermissionError(f"Live Alpaca host {cfg.endpoint_or_host!r} is hard-refused")
    if cfg.port in (4001, 7496):
        raise PermissionError(f"Live IBKR port {cfg.port} is hard-refused; paper port 4002 only")

    if isinstance(cfg.protective_stop_pct, bool) or not math.isfinite(cfg.protective_stop_pct):
        raise ValueError("protective_stop_pct must be finite")
    stop_dec = Decimal(str(cfg.protective_stop_pct))
    if stop_dec <= Decimal("0") or stop_dec > MAX_PROTECTIVE_STOP_DEC:
        raise ValueError(f"protective_stop_pct {cfg.protective_stop_pct:.4f} violates (0, 0.0200] ADR-0022 cap")

    if cfg.broker == "alpaca_paper":
        if cfg.venue_prefix != "PA":
            raise PermissionError(
                f"Non-paper venue_prefix {cfg.venue_prefix!r} is hard-refused; Alpaca paper requires 'PA'"
            )
        if cfg.endpoint_or_host != "paper-api.alpaca.markets":
            raise ValueError(f"Expected endpoint 'paper-api.alpaca.markets', got {cfg.endpoint_or_host!r}")
        if cfg.max_rate_per_min > ALPACA_PAPER_MAX_RPM:
            raise ValueError(f"Alpaca max_rate_per_min {cfg.max_rate_per_min} exceeds {ALPACA_PAPER_MAX_RPM}")
        max_entry = ALPACA_PAPER_MAX_RPM - PROTECTIVE_EXIT_RESERVE_RPM
        if cfg.entry_rate_cap_per_min <= 0 or cfg.entry_rate_cap_per_min > max_entry:
            raise ValueError(f"Alpaca entry_rate_cap_per_min {cfg.entry_rate_cap_per_min} must be in [1, {max_entry}]")
        if cfg.rth_contingency != "OTO":
            raise ValueError(f"Alpaca RTH contingency must be 'OTO', got {cfg.rth_contingency!r}")
        if cfg.extended_session_protection != "awake_limit_guardian_24x5":
            raise ValueError("Alpaca extended/overnight requires 'awake_limit_guardian_24x5'")
    else:
        if cfg.venue_prefix != "DU":
            raise PermissionError(
                f"Non-paper venue_prefix {cfg.venue_prefix!r} is hard-refused; IBKR paper requires 'DU'"
            )
        if cfg.port != 4002:
            raise ValueError(f"IBKR paper requires port 4002, got {cfg.port!r}")
        if cfg.max_rate_per_min > IBKR_PAPER_MAX_MPM:
            raise ValueError(f"IBKR max_rate_per_min {cfg.max_rate_per_min} exceeds {IBKR_PAPER_MAX_MPM}")
        if cfg.entry_rate_cap_per_min <= 0 or cfg.entry_rate_cap_per_min >= cfg.max_rate_per_min:
            raise ValueError("IBKR entry_rate_cap_per_min must reserve protective exit capacity")
        if cfg.extended_session_protection != "outside_rth_stop_limit":
            raise ValueError("IBKR extended session requires 'outside_rth_stop_limit'")


@dataclass(frozen=True, slots=True)
class StrategyLifecycleRecord:
    strategy_id: str
    trial_n: int
    spec_sha256: str
    target_stage: LifecycleStage
    nautilus_pin: str
    hftbacktest_pin: str
    queue_model: str
    calibration_max_date: dt.date
    events_count: int
    distinct_dates: int
    cpcv_folds: int
    cpcv_test_folds: int
    cpcv_positive_share: float
    dsr_probability: float
    t_stat_clustered: float
    net_return_1x_bps: float
    net_return_2x_bps: float
    verified_model_families: tuple[str, ...]
    open_p0_p1_defects: int
    brokers: tuple[BrokerTargetConfig, ...]
    forward_shadow_start: dt.date | None = None
    eb_prior_mean_bps: float | None = None
    eb_prior_std_bps: float | None = None
    eb_obs_mean_bps: float | None = None
    eb_obs_se_bps: float | None = None
    lesson_recorded: bool = False


@dataclass(frozen=True, slots=True)
class PromotionVerdict:
    strategy_id: str
    target_stage: LifecycleStage
    approved: bool
    highest_cleared_stage: LifecycleStage | None
    required_hlz_t: float
    eb_posterior_mean_bps: float | None
    reasons: tuple[str, ...]


def evaluate_strategy_promotion(record: StrategyLifecycleRecord) -> PromotionVerdict:
    """Evaluate all cumulative gates required to reach ``record.target_stage``."""
    reasons: list[str] = []
    req_t = hlz_t_hurdle(record.trial_n)
    target_idx = STAGE_ORDER.index(record.target_stage)
    highest: LifecycleStage | None = None
    eb_post: float | None = None

    # Stage 0: Pre-registration
    if not _SHA256_RE.match(record.spec_sha256):
        reasons.append("Stage 0: spec_sha256 must be a 64-character lowercase hex SHA-256 digest")
    else:
        highest = LifecycleStage.HYPOTHESIS

    # Stage 1: Sim & upstream queue parity
    if target_idx >= 1 and not reasons:
        if record.nautilus_pin != NAUTILUS_PIN:
            reasons.append(f"Stage 1: nautilus_pin {record.nautilus_pin!r} != {NAUTILUS_PIN!r}")
        if record.hftbacktest_pin != HFTBACKTEST_PIN:
            reasons.append(f"Stage 1: hftbacktest_pin {record.hftbacktest_pin!r} != {HFTBACKTEST_PIN!r}")
        if record.queue_model not in ("RiskAdverseQueueModel", "LogProbQueueModel2"):
            reasons.append(f"Stage 1: unsupported queue_model {record.queue_model!r}")
        if not reasons:
            highest = LifecycleStage.SIM_QUEUE_PARITY

    # Stage 2: Pre-wall CPCV / DSR / HLZ / 2x-impact backtest
    if target_idx >= 2 and not reasons:
        if record.calibration_max_date > STUDY_WALL:
            reasons.append(
                f"Stage 2: calibration_max_date {record.calibration_max_date.isoformat()} > {STUDY_WALL.isoformat()}"
            )
        if record.events_count < 200 or record.distinct_dates < 60:
            reasons.append(
                f"Stage 2: sample ({record.events_count} events / {record.distinct_dates} dates) < (200 / 60)"
            )
        if (record.cpcv_folds, record.cpcv_test_folds) != (6, 2):
            reasons.append("Stage 2: CPCV geometry must be (n_folds=6, n_test_folds=2)")
        if not math.isfinite(record.cpcv_positive_share) or not (0.80 <= record.cpcv_positive_share <= 1.0):
            reasons.append(f"Stage 2: cpcv_positive_share {record.cpcv_positive_share} < 0.80")
        if not math.isfinite(record.dsr_probability) or not (0.95 <= record.dsr_probability <= 1.0):
            reasons.append(f"Stage 2: dsr_probability {record.dsr_probability} < 0.95")
        if not math.isfinite(record.t_stat_clustered) or record.t_stat_clustered < req_t:
            reasons.append(f"Stage 2: t_stat_clustered {record.t_stat_clustered:.4f} < HLZ t*={req_t:.4f}")
        if not math.isfinite(record.net_return_1x_bps) or record.net_return_1x_bps <= 0.0:
            reasons.append(f"Stage 2: net_return_1x_bps {record.net_return_1x_bps} <= 0")
        if not math.isfinite(record.net_return_2x_bps) or record.net_return_2x_bps <= 0.0:
            reasons.append(f"Stage 2: net_return_2x_bps {record.net_return_2x_bps} <= 0")
        if not reasons:
            highest = LifecycleStage.PREWALL_BACKTEST

    # Stage 3: Cross-model adversarial falsification
    if target_idx >= 3 and not reasons:
        distinct_families = {fam.strip().lower() for fam in record.verified_model_families if fam.strip()}
        if len(distinct_families) < 3:
            reasons.append(f"Stage 3: requires >= 3 distinct model families, got {sorted(distinct_families)}")
        if record.open_p0_p1_defects != 0:
            reasons.append(f"Stage 3: open_p0_p1_defects={record.open_p0_p1_defects} (must be 0)")
        if not reasons:
            highest = LifecycleStage.MULTIMODEL_FALSIFICATION

    # Stage 4: Paper broker execution (Alpaca Paper / IBKR Paper)
    if target_idx >= 4 and not reasons:
        if not record.brokers:
            reasons.append("Stage 4: at least one paper broker target is required")
        for b_cfg in record.brokers:
            # Propagate PermissionError immediately if live capital is ever attempted
            try:
                validate_broker_target(b_cfg)
            except ValueError as exc:
                reasons.append(f"Stage 4 ({b_cfg.broker}): {exc}")
        if record.forward_shadow_start is None or record.forward_shadow_start <= STUDY_WALL:
            reasons.append("Stage 4: forward_shadow_start must be strictly post-wall (>= 2026-10-16)")
        if not reasons:
            highest = LifecycleStage.PAPER_BROKER_EXECUTION

    # Stage 5: Empirical-Bayes fine-tuning & SkillOpt compounding
    if target_idx >= 5 and not reasons:
        if (
            record.eb_prior_mean_bps is None
            or record.eb_prior_std_bps is None
            or record.eb_obs_mean_bps is None
            or record.eb_obs_se_bps is None
        ):
            reasons.append("Stage 5: Empirical-Bayes prior/observation parameters are required")
        else:
            eb_post, _ = empirical_bayes_shrink_edge(
                prior_mean_bps=record.eb_prior_mean_bps,
                prior_std_bps=record.eb_prior_std_bps,
                obs_mean_bps=record.eb_obs_mean_bps,
                obs_se_bps=record.eb_obs_se_bps,
            )
            if eb_post <= 0.0:
                reasons.append(f"Stage 5: shrunken Empirical-Bayes posterior edge {eb_post:.4f} bps <= 0")
        if not record.lesson_recorded:
            reasons.append("Stage 5: lesson_recorded must be True in LESSONS.md / HYPOTHESIS_LEDGER.md")
        if not reasons:
            highest = LifecycleStage.COMPOUNDING_FINETUNE

    return PromotionVerdict(
        strategy_id=record.strategy_id,
        target_stage=record.target_stage,
        approved=len(reasons) == 0,
        highest_cleared_stage=highest,
        required_hlz_t=req_t,
        eb_posterior_mean_bps=eb_post,
        reasons=tuple(reasons),
    )


def validate_compounding_manifest(
    manifest_path: pathlib.Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Validate config/strategy-compounding-manifest.json invariants and org coordination."""
    path = manifest_path or DEFAULT_MANIFEST_PATH
    errors: list[str] = []
    if not path.is_file():
        return {}, [f"Missing compounding manifest: {path}"]

    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("studyWallDate") != STUDY_WALL.isoformat():
        errors.append(f"studyWallDate must equal {STUDY_WALL.isoformat()}")

    org = data.get("githubOrganization", {})
    if org.get("name") != "native-agent-stack" or org.get("url") != "https://github.com/native-agent-stack":
        errors.append("githubOrganization must point to https://github.com/native-agent-stack")
    pub_repos = org.get("publicUnlimitedCiRepos", [])
    priv_repos = org.get("privateAlphaAndVaultRepos", [])
    if not pub_repos or not priv_repos:
        errors.append("githubOrganization must declare non-empty publicUnlimitedCiRepos and privateAlphaAndVaultRepos")
    overlap = set(pub_repos) & set(priv_repos)
    if overlap:
        errors.append(f"Public/Private repo overlap detected: {sorted(overlap)}")

    # Validate broker execution targets
    brokers_raw = data.get("paperBrokerTargets", [])
    if len(brokers_raw) < 2:
        errors.append("paperBrokerTargets must configure both alpaca_paper and ibkr_paper")
    broker_objs: list[BrokerTargetConfig] = []
    for raw_b in brokers_raw:
        cfg = BrokerTargetConfig(
            broker=raw_b["broker"],
            venue_prefix=raw_b["venuePrefix"],
            endpoint_or_host=raw_b["endpointOrHost"],
            port=raw_b.get("port"),
            max_rate_per_min=int(raw_b["maxRatePerMin"]),
            entry_rate_cap_per_min=int(raw_b["entryRateCapPerMin"]),
            protective_stop_pct=float(raw_b["protectiveStopPct"]),
            rth_contingency=raw_b["rthContingency"],
            extended_session_protection=raw_b["extendedSessionProtection"],
        )
        try:
            validate_broker_target(cfg)
            broker_objs.append(cfg)
        except (PermissionError, ValueError) as exc:
            errors.append(f"Broker config invalid ({raw_b.get('broker')}): {exc}")

    # Validate archived pre-wall trials are deterministically blocked from Stage-4 paper promotion
    for trial in data.get("empiricalTrialsArchive", []):
        rec = StrategyLifecycleRecord(
            strategy_id=trial["strategyId"],
            trial_n=int(trial["trialN"]),
            spec_sha256=trial["specSha256"],
            target_stage=LifecycleStage.PAPER_BROKER_EXECUTION,
            nautilus_pin=NAUTILUS_PIN,
            hftbacktest_pin=HFTBACKTEST_PIN,
            queue_model=trial["queueModel"],
            calibration_max_date=dt.date.fromisoformat(trial["calibrationMaxDate"]),
            events_count=int(trial["eventsCount"]),
            distinct_dates=int(trial["distinctDates"]),
            cpcv_folds=6,
            cpcv_test_folds=2,
            cpcv_positive_share=float(trial["cpcvPositiveShare"]),
            dsr_probability=float(trial["dsrProbability"]),
            t_stat_clustered=float(trial["tStatClustered"]),
            net_return_1x_bps=float(trial["netReturn1xBps"]),
            net_return_2x_bps=float(trial["netReturn2xBps"]),
            verified_model_families=tuple(trial["verifiedModelFamilies"]),
            open_p0_p1_defects=0,
            brokers=tuple(broker_objs),
            forward_shadow_start=dt.date(2026, 10, 16),
        )
        verdict = evaluate_strategy_promotion(rec)
        if trial.get("status") == "REJECTED_PREWALL" and verdict.approved:
            errors.append(f"Rejected pre-wall trial {rec.strategy_id} unexpectedly passed Stage-4 gate")

    # Validate next pre-registration candidate queue
    candidates = data.get("nextHypothesisQueue", [])
    if not candidates:
        errors.append("nextHypothesisQueue must contain >= 1 pre-registration candidate")
    for cand in candidates:
        expected_t = hlz_t_hurdle(int(cand["nextTrialN"]))
        if abs(float(cand["requiredHlzTHurdle"]) - expected_t) > 1e-4:
            errors.append(
                f"Candidate {cand['strategyId']} hurdle {cand['requiredHlzTHurdle']} != {expected_t}"
            )
        cal_stop = calibrate_protective_trail_pct(
            prewall_median_bar_range_bps=float(cand["prewallMedianBarRangeBps"]),
            range_multiplier=float(cand["rangeMultiplier"]),
        )
        if cal_stop > MAX_PROTECTIVE_STOP_PCT:
            errors.append(f"Candidate {cand['strategyId']} calibrated stop {cal_stop} > 0.0200")

    return data, errors


def validate_legacy_harvest_manifest(
    manifest_path: pathlib.Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Validate config/legacy-harvest-manifest.json 40-char SHAs and supersession map."""
    path = manifest_path or DEFAULT_LEGACY_HARVEST_PATH
    errors: list[str] = []
    if not path.is_file():
        return {}, [f"Missing legacy harvest manifest: {path}"]

    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("harvestedRepositories", [])
    if len(records) < 45:
        errors.append(f"Expected >= 45 harvested legacy repository records, found {len(records)}")

    seen_keys: set[str] = set()
    for row in records:
        repo_key = str(row.get("legacyRepo", ""))
        if not repo_key or repo_key in seen_keys:
            errors.append(f"Duplicate or empty legacyRepo entry: {repo_key!r}")
        seen_keys.add(repo_key)

        sha = str(row.get("frozenCommitSha", ""))
        if sha != "EMPTY_REPO" and not _SHA1_40_RE.match(sha):
            errors.append(f"Invalid 40-char frozenCommitSha for {repo_key}: {sha!r}")

        succ = str(row.get("supersededBy", ""))
        if not succ.startswith("native-agent-stack/"):
            errors.append(f"{repo_key} supersededBy must target native-agent-stack/*, got {succ!r}")

        if row.get("archivedReadOnly") is not True:
            errors.append(f"{repo_key} must have archivedReadOnly=true")

    invariants = data.get("harvestedInvariants", [])
    if len(invariants) < 6:
        errors.append("harvestedInvariants must document >= 6 code-enforced legacy lessons")
    return data, errors
