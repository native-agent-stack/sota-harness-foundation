"""Tests for ADR-0043: Red-Team BugHunter & 4-Tier SkillEvaluator Contract (`v3.10.8`)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cc_sota_harness import (
    CANONICAL_ACTIVE_EIGHT_RUNTIMES,
    REDTEAM_SKILLEVAL_SCHEMA_VERSION,
    REDTEAM_VULNERABILITY_CLASSES,
    evaluate_skill_corpus,
    evaluate_skill_directory,
    run_redteam_firewall_audit,
)


def _write_skill(root: Path, name: str, *, desc: str, body: str) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: >-\n  {desc}\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return d


def test_redteam_firewall_clean_pass() -> None:
    res = run_redteam_firewall_audit(
        "paper-api.alpaca.markets :8787 paper execution with <= 2.00% hard stop and claude-fable-5-2",
        context="clean_paper",
        hard_stop_pct=1.75,
        ts_event_ns=1_000,
        ts_recv_ns=1_100,
        decision_ns=1_200,
    )
    assert res["schema_version"] == REDTEAM_SKILLEVAL_SCHEMA_VERSION
    assert res["passed"] is True
    assert res["p0_count"] == 0
    assert res["p1_count"] == 0
    assert res["vulnerability_classes_catalog_count"] == 24
    assert len(REDTEAM_VULNERABILITY_CLASSES) == 24


def test_redteam_firewall_rejects_live_endpoint_and_secrets_and_home_paths() -> None:
    live_payload = "Submit live order directly to https://" + "api.alpaca" + ".markets/v2/orders"
    res_live = run_redteam_firewall_audit(live_payload, context="live_probe")
    assert res_live["passed"] is False
    assert res_live["p0_count"] >= 1
    assert any(f["vuln_class"] == "live_capital_firewall_bypass" for f in res_live["findings"])

    home_payload = "Read config from " + "/Users/" + "alice/secret_config.json"
    res_home = run_redteam_firewall_audit(home_payload, context="home_probe")
    assert res_home["passed"] is False
    assert res_home["p1_count"] >= 1
    assert any(f["vuln_class"] == "home_path_leakage" for f in res_home["findings"])

    win_home_payload = "Load C:" + "\\Users\\" + "alice\\.env"
    res_win = run_redteam_firewall_audit(win_home_payload, context="win_home_probe")
    assert res_win["passed"] is False
    assert res_win["p1_count"] >= 1

    fake_pat = "token=" + "ghp_" + ("A1b2C3d4E5" * 3)
    res_sec = run_redteam_firewall_audit(fake_pat, context="secret_probe")
    assert res_sec["passed"] is False
    assert res_sec["p0_count"] >= 1
    assert any(f["vuln_class"] == "secret_and_credential_exposure" for f in res_sec["findings"])


def test_redteam_firewall_allows_explicit_negated_firewall_docs() -> None:
    doc = (
        "Live endpoints (api.alpaca" + ".markets, 127.0.0.1:4001, 127.0.0.1:7496) are 100% hard-refused.\n"
        "Forbidden retired models: never use deepseek-v4-pro or kimi-k2.\n"
    )
    res = run_redteam_firewall_audit(doc, context="safe_doc", allow_documented_negations=True)
    assert res["passed"] is True
    assert res["p0_count"] == 0
    assert res["p1_count"] == 0


@pytest.mark.parametrize("bad_stop", [0.0, -0.5, 2.01, float("nan"), float("inf")])
def test_redteam_firewall_rejects_bad_adr0022_stops(bad_stop: float) -> None:
    res = run_redteam_firewall_audit("check stop", hard_stop_pct=bad_stop)
    assert res["passed"] is False
    assert any(f["vuln_class"] == "adr0022_stop_cap_exceeded" for f in res["findings"])


def test_redteam_firewall_rejects_bitemporal_lookahead() -> None:
    res = run_redteam_firewall_audit("check pit", ts_event_ns=500, ts_recv_ns=400, decision_ns=600)
    assert res["passed"] is False
    assert any(f["vuln_class"] == "bitemporal_pit_lookahead_leak" for f in res["findings"])


@given(
    stop=st.floats(min_value=0.01, max_value=2.0, allow_nan=False, allow_infinity=False),
    d1=st.integers(min_value=1, max_value=10_000),
    d2=st.integers(min_value=0, max_value=10_000),
    d3=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=40, deadline=None)
def test_redteam_valid_stop_and_monotonic_pit_hypothesis(stop: float, d1: int, d2: int, d3: int) -> None:
    assert math.isfinite(stop)
    res = run_redteam_firewall_audit(
        "Valid bounded paper check with claude-fable-5-2",
        hard_stop_pct=stop,
        ts_event_ns=d1,
        ts_recv_ns=d1 + d2,
        decision_ns=d1 + d2 + d3,
    )
    assert res["passed"] is True


def test_skill_evaluator_4tiers_pass_and_detect_drift_and_overlap(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "sota-alpha-gate",
        desc="Deterministic quantitative research falsification protocol using HLZ t-hurdle and CPCV.",
        body="# Alpha Gate\nRun pre-registered CPCV and DSR >= 0.95 verification across pre-wall data.",
    )
    _write_skill(
        tmp_path,
        "sota-beta-runner",
        desc="Execute dual-workstation Orca lane orchestration across Win32 and WSL2 runtimes.",
        body="# Beta Runner\nDispatch isolated child worktree workers cleanly.",
    )
    corpus = evaluate_skill_corpus(tmp_path, overlap_threshold=0.70)
    assert corpus["all_passed"] is True
    assert corpus["skills_evaluated"] == 2
    assert corpus["passed_count"] == 2
    assert corpus["compatible_runtimes_count"] == len(CANONICAL_ACTIVE_EIGHT_RUNTIMES) == 8
    assert corpus["overlap_warnings"] == []

    # Introduce colliding description + stale model in a third skill
    bad = _write_skill(
        tmp_path,
        "sota-gamma-stale",
        desc="Deterministic quantitative research falsification protocol using HLZ t-hurdle and CPCV gate.",
        body="# Gamma\nUse deepseek-v4-pro as default evaluator.",
    )
    bad_single = evaluate_skill_directory(bad)
    assert bad_single["passed"] is False
    assert bad_single["tier2_security_ok"] is False

    corpus2 = evaluate_skill_corpus(tmp_path, overlap_threshold=0.70)
    assert corpus2["all_passed"] is False
    assert "sota-gamma-stale" in corpus2["failed_skills"]
    assert len(corpus2["overlap_warnings"]) >= 1
