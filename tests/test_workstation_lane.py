"""Unit and Hypothesis property tests for the Dual-Machine Orca Workstation Lane (ADR-0020)."""

from __future__ import annotations

import json
import pathlib
import subprocess
from unittest import mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cc_sota_harness.h090_tight_spread_passive_bid_prewall import (
    ADR0022_CATASTROPHE_STOP_RATIO,
    H090_HYPOTHESIS_ID,
    H090_SPEC_SHA256,
    replay_adr0022_catastrophe_eod_exit,
)
from cc_sota_harness.passive_bid_trail_prewall import AdverseBar1m, QuoteTickNs
from cc_sota_harness.workstation_lane import (
    CANONICAL_HARNESS_LANES,
    CANONICAL_ORCHESTRATION_FRAMEWORKS,
    CANONICAL_TRADING_LANES,
    PORTABLE_MAC_MAX_THREADS_AC,
    PORTABLE_MAC_MAX_THREADS_BATTERY,
    PORTABLE_MAC_MAX_THREADS_LOW_BATTERY,
    STATIONARY_NOESIS_MAX_THREADS,
    HostTelemetry,
    WorkloadKind,
    WorkstationTopologyMode,
    build_noesis_sync_powershell_commands,
    build_orca_coop_sync_plan,
    classify_topology_mode,
    enforce_workstation_wsl_and_gateway_guard,
    filter_lease_safe_sync_repos,
    portable_thread_budget,
    probe_noesis_orca_with_retry,
    resolve_local_mac_repo_dir,
    resolve_orca_lane_topology,
    resolve_prewall_lake_root,
    resolve_workstation_placement,
    resolve_workstation_repo_dir,
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
    enforce_workstation_wsl_and_gateway_guard(
        "wsl -d meridian -e pytest -q", {"ANTHROPIC_BASE_URL": "http://127.0.0.1:20128"}
    )

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


def test_probe_noesis_retry_local_mac_repo_dirs_and_powershell_sync(tmp_path: pathlib.Path) -> None:
    # 1. Retry recovers cleanly after initial Tailscale idle-wakeup timeout (timeout=12s)
    ok_payload = json.dumps({"ok": True, "result": {"repos": [{"name": "sota-multi-model-workflows"}]}})
    side_effects = [
        subprocess.TimeoutExpired(cmd=["orca"], timeout=12.0),
        subprocess.CompletedProcess(args=["orca"], returncode=0, stdout=ok_payload, stderr=""),
    ]
    with mock.patch("cc_sota_harness.workstation_lane.subprocess.run", side_effect=side_effects) as m_run:
        reachable, rtt_ms, repos = probe_noesis_orca_with_retry("orca", "100.110.115.22")
        assert reachable is True
        assert rtt_ms is not None
        assert len(repos) == 1
        assert m_run.call_count == 2
        assert m_run.call_args.kwargs["timeout"] == 12.0

    # 2. Local macOS checkout path mapping including TCC-safe & dsh-plugin-landscape fallback
    assert resolve_local_mac_repo_dir("sota-dynamic-trail-c", tmp_path) == tmp_path / "sota-dynamic-trail-c"
    assert resolve_local_mac_repo_dir("canon", tmp_path) == tmp_path / "canon"
    assert resolve_local_mac_repo_dir(".github", tmp_path) == tmp_path / "Documents" / "dot-github"
    assert resolve_local_mac_repo_dir("dsh-plugin-landscape", tmp_path) == tmp_path / "Documents" / "dsh"
    (tmp_path / "Documents" / "dsh-plugin-landscape" / ".git").mkdir(parents=True)
    assert (
        resolve_local_mac_repo_dir("dsh-plugin-landscape", tmp_path) == tmp_path / "Documents" / "dsh-plugin-landscape"
    )

    # 3. Noesis PowerShell sync includes workflows/* -> $HOME/.agents/workflows/ & ===SYNC_DONE===
    cmds = build_noesis_sync_powershell_commands(
        [".github", "sota-multi-model-workflows", "sota-mover-ranker"],
        skip_leased_repos=["sota-mover-ranker"],
    )
    joined = "\n".join(cmds)
    assert "git -C C:/sota-workstation/dot-github pull --ff-only" in joined
    assert "git -C C:/sota-workstation/sota-multi-model-workflows pull --ff-only" in joined
    assert "sota-mover-ranker" not in joined
    assert (
        'Copy-Item -Force C:/sota-workstation/sota-multi-model-workflows/workflows/* "$HOME/.agents/workflows/"'
        in joined
    )
    assert 'Write-Output "===SYNC_DONE==="' in joined


def test_v360_headless_orca_lease_safe_sync_and_3surface_resolver(tmp_path: pathlib.Path) -> None:
    validate_headless_orca_serve_flags(
        ["orca", "serve", "--host", "100.110.115.22", "--port", "6770", "--no-pairing", "--refuse-public"]
    )
    with pytest.raises(PermissionError, match="--refuse-public"):
        validate_headless_orca_serve_flags(["orca", "serve", "--host", "100.110.115.22", "--no-pairing"])
    safe, skipped = filter_lease_safe_sync_repos(
        ["sota-harness-foundation", "sota-mover-ranker"],
        remote_active_leases=[{"repo": "sota-mover-ranker", "lease_key": "sota-mover-ranker::agy-noesis-24x5"}],
    )
    assert safe == ["sota-harness-foundation"]
    assert "sota-mover-ranker" in skipped

    wsl_home = tmp_path / "wsl"
    win_root = tmp_path / "win"
    (wsl_home / "sota-workstation" / "meridian").mkdir(parents=True)
    (win_root / "astrolabe").mkdir(parents=True)
    assert resolve_workstation_repo_dir("meridian", home=wsl_home, win_root=win_root) == (
        wsl_home / "sota-workstation" / "meridian"
    )
    assert resolve_workstation_repo_dir("astrolabe", home=wsl_home, win_root=win_root) == win_root / "astrolabe"


def test_adr_0029_orca_lane_topology_rth_broker_shield_and_3surface_lake(tmp_path: pathlib.Path) -> None:
    # 1. Idle docked Mac (no active broker) keeps interactive research local; active RTH broker offloads 56t to Noesis
    idle_docked = HostTelemetry(
        on_ac_power=True, battery_pct=100.0, paired_host_reachable=True, paired_rtt_ms=11.0, active_broker_host=None
    )
    assert resolve_workstation_placement(idle_docked, WorkloadKind.HEAVY_PREWALL_RESEARCH).target_host == (
        "portable_mac_lead"
    )

    rth_docked = HostTelemetry(
        on_ac_power=True,
        battery_pct=100.0,
        paired_host_reachable=True,
        paired_rtt_ms=11.0,
        active_broker_host="portable_mac_lead",
    )
    topo = resolve_orca_lane_topology(rth_docked)
    assert topo["reposPartitionedTotal"] == 18
    assert topo["frameworksTotal"] == len(CANONICAL_ORCHESTRATION_FRAMEWORKS) == 8
    assert topo["distinctVendorsTotal"] >= 7
    assert len(CANONICAL_TRADING_LANES) == 5
    assert len(CANONICAL_HARNESS_LANES) == 8
    assert topo["tradingLanes"]["T1_MERIDIAN_NAUTILUS_QUEUE_SIM"]["targetHost"] == "stationary_noesis_heavy"
    assert topo["tradingLanes"]["T2_PREWALL_CAUSAL_ALPHA_LAB"]["targetHost"] == "stationary_noesis_heavy"
    assert topo["tradingLanes"]["T2_PREWALL_CAUSAL_ALPHA_LAB"]["allocatedThreads"] == STATIONARY_NOESIS_MAX_THREADS
    assert topo["tradingLanes"]["T3A_ALPACA_200RPM_SIP_PAPER"]["targetHost"] == "portable_mac_lead"
    assert topo["tradingLanes"]["T3B_IBKR_4002_NAUTILUS_PAPER"]["targetHost"] == "portable_mac_lead"
    assert topo["tradingLanes"]["T4_T5_COMPOUNDING_GUARDIAN_VAULT"]["targetHost"] == "portable_mac_lead"

    # 2. 3-surface pre-wall Parquet lake path resolution (WSL2 -> Win32 -> Mac fallback)
    fake_home = tmp_path / "home"
    wsl_lake = tmp_path / "mnt_z_prewall"
    win_lake = tmp_path / "win_z_prewall"
    assert resolve_prewall_lake_root(home=fake_home, wsl_lake=wsl_lake, win_lake=win_lake) == (
        fake_home / "Documents" / "market-data"
    )
    win_lake.mkdir(parents=True)
    assert resolve_prewall_lake_root(home=fake_home, wsl_lake=wsl_lake, win_lake=win_lake) == win_lake
    wsl_lake.mkdir(parents=True)
    assert resolve_prewall_lake_root(home=fake_home, wsl_lake=wsl_lake, win_lake=win_lake) == wsl_lake


@given(
    pullback_bps=st.floats(min_value=5.0, max_value=185.0, allow_nan=False, allow_infinity=False),
    eod_gain_bps=st.floats(min_value=10.0, max_value=450.0, allow_nan=False, allow_infinity=False),
)
def test_property_h090_adr0022_catastrophe_hold_survives_intraday_noise(
    pullback_bps: float, eod_gain_bps: float
) -> None:
    assert H090_HYPOTHESIS_ID == "H090_TIGHT_SPREAD_HIGH_OFI_PASSIVE_BID_ADR0022_EOD_HOLD"
    assert len(H090_SPEC_SHA256) == 64
    entry_px = 100.0
    pullback_px = entry_px * (1.0 - pullback_bps / 10_000.0)
    close_px = entry_px * (1.0 + eod_gain_bps / 10_000.0)
    res = replay_adr0022_catastrophe_eod_exit(
        entry_px=entry_px,
        fill_ts_ns=1_000,
        post_fill_quotes=[QuoteTickNs(ts_ns=1_500, bid_px=101.20, bid_lots=5.0, ask_px=101.25, ask_lots=5.0)],
        intraday_bars=[
            AdverseBar1m(ts_ns=60_000_000_000, open_px=101.0, high_px=102.0, low_px=pullback_px, close_px=close_px)
        ],
        fallback_close_px=close_px,
        exit_cost_1x_bps=5.5,
    )
    assert res.exit_reason == "time_flatten_1554"
    assert abs(res.gross_return_bps - eod_gain_bps) < 1e-6

    crash = replay_adr0022_catastrophe_eod_exit(
        entry_px=entry_px,
        fill_ts_ns=1_000,
        post_fill_quotes=[],
        intraday_bars=[AdverseBar1m(ts_ns=60_000_000_000, open_px=99.5, low_px=97.5, high_px=104.0, close_px=103.0)],
        fallback_close_px=103.0,
        exit_cost_1x_bps=5.5,
    )
    assert crash.exit_reason == "bar_adr0022_catastrophe_stop"
    assert abs(crash.gross_return_bps - (-ADR0022_CATASTROPHE_STOP_RATIO * 10_000.0)) < 1e-6

    with pytest.raises(ValueError, match="Invalid"):
        replay_adr0022_catastrophe_eod_exit(
            entry_px=entry_px,
            fill_ts_ns=1_000,
            post_fill_quotes=[],
            intraday_bars=[],
            fallback_close_px=100.0,
            exit_cost_1x_bps=5.0,
            catastrophe_stop_ratio=0.025,
        )


def test_adr_0034_coop_recipient_omc_callback_and_3surface_memory_sync() -> None:
    from cc_sota_harness.workstation_lane import (
        build_memory_delta_sync_plan,
        normalize_coop_recipient,
        validate_omc_stop_callback_config,
    )

    assert normalize_coop_recipient("mac-m5-agy", direction="inbound_to_mac") == "agy"
    assert normalize_coop_recipient("cc-lead", direction="inbound_to_mac") == "cc-lead"
    assert normalize_coop_recipient("", direction="outbound_to_noesis") == "*"

    ok, errs = validate_omc_stop_callback_config(
        {
            "claudeMdEnabled": False,
            "stopHookCallbacks": {
                "file": {
                    "enabled": True,
                    "path": "~/.agents/bus/omc_stop_callbacks/{session_id}-{date}-{time}.json",
                    "format": "json",
                }
            },
        }
    )
    assert ok is True and errs == []
    bad_ok, bad_errs = validate_omc_stop_callback_config({"claudeMdEnabled": True})
    assert bad_ok is False and len(bad_errs) >= 2

    plan = build_memory_delta_sync_plan(since_hours=1.5, qmd_indexed_docs=567)
    assert plan["conptyTempFileRelay"] is True
    assert len(plan["surfaces"]) == 3
    assert plan["qmdIndexedDocs"] >= 567


def test_adr_0035_createprocessw_chunked_b64_and_qmd_bm25_tokenizer() -> None:
    from cc_sota_harness.workstation_lane import (
        chunk_powershell_b64_payload,
        tokenize_qmd_bm25_query,
    )

    big_b64 = "A" * 9000
    lines = chunk_powershell_b64_payload(big_b64, max_chunk_chars=3500)
    assert len(lines) == 3
    assert lines[0].startswith("Set-Content -NoNewline")
    assert lines[1].startswith("Add-Content -NoNewline")
    assert all(len(ln) < 4000 for ln in lines)

    kw = tokenize_qmd_bm25_query(
        "sota-harness-foundation",
        "Verify ADR-0035 CreateProcessW chunked sync and qmd BM25",
    )
    assert "sota-harness-foundation" in kw
    assert "ADR-0035" in kw


def test_adr_0036_claude_1to1_fable_telemetry_and_tier_validator() -> None:
    from cc_sota_harness.workstation_lane import (
        compute_claude_fable_1to1_telemetry,
        validate_claude_1to1_tier_config,
    )

    ok_tier, tier_errs = validate_claude_1to1_tier_config(
        {
            "OMC_MODEL_HIGH": "claude-fable-5-2",
            "OMC_MODEL_MEDIUM": "claude-sonnet-5-5",
            "OMC_MODEL_LOW": "claude-sonnet-5-5",
        }
    )
    assert ok_tier is True and tier_errs == []
    bad_ok, bad_errs = validate_claude_1to1_tier_config({"OMC_MODEL_LOW": "claude-haiku-5-5"})
    assert bad_ok is False and len(bad_errs) == 3

    skew = compute_claude_fable_1to1_telemetry({"claude-fable-5-2": 2, "claude-opus-5-5": 126, "claude-haiku-5-5": 285})
    assert skew["within1To1Band"] is False
    assert skew["haikuTurns"] == 285

    bal = compute_claude_fable_1to1_telemetry({"claude-fable-5-2": 50, "claude-opus-5-5": 20, "claude-sonnet-5-5": 30})
    assert bal["within1To1Band"] is True
    assert bal["fableShare"] == 0.50
    assert bal["haikuTurns"] == 0
