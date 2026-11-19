"""Unit tests for ADR-0042: Agent-Native 5-Layer Computer-Use & Tiered Zero-Friction Permissions."""

from __future__ import annotations

from typing import Any

import pytest

from cc_sota_harness import (
    COMPUTER_USE_SCHEMA_VERSION,
    HUMAN_TRUST_GATE_CATEGORIES,
    SANCTIONED_ZERO_FRICTION_CATEGORIES,
    UPSTREAM_COMPUTER_USE_REFERENCE_STACK,
    ComputerUseRouteDecision,
    ComputerUseTier,
    GatedActionDecision,
    PermissionTier,
    build_computer_use_manifest,
    evaluate_gated_action_policy,
    resolve_computer_use_tier,
)


def test_resolve_computer_use_tier_escalation_ladder() -> None:
    d1 = resolve_computer_use_tier(
        has_cli_rpc_or_mcp=True,
        is_web_browser_task=True,
        has_accessibility_tree=True,
        host_platform="win32",
        background_supported=False,
    )
    assert isinstance(d1, ComputerUseRouteDecision)
    assert d1.tier is ComputerUseTier.L1_PROGRAMMATIC_CLI_RPC_MCP
    assert d1.transport == "cli_or_zero_terminal_rpc_or_mcp"
    assert d1.prefer_background is True
    assert d1.distill_to_cli_if_recurring is False

    d_web = resolve_computer_use_tier(
        has_cli_rpc_or_mcp=False,
        is_web_browser_task=True,
        has_accessibility_tree=True,
        host_platform="darwin",
        background_supported=True,
    )
    assert d_web.tier is ComputerUseTier.L3_COMPACT_BROWSER_CDP_REFS
    assert d_web.transport == "orca_browser_or_agent_browser_or_playwright_cli"

    d_mac_ax = resolve_computer_use_tier(
        has_cli_rpc_or_mcp=False,
        is_web_browser_task=False,
        has_accessibility_tree=True,
        host_platform="darwin",
        background_supported=True,
    )
    assert d_mac_ax.tier is ComputerUseTier.L2_SEMANTIC_ACCESSIBILITY_BACKGROUND
    assert d_mac_ax.transport == "orca_computer_macos_background"
    assert d_mac_ax.prefer_background is True
    assert d_mac_ax.distill_to_cli_if_recurring is True

    d_win_ax = resolve_computer_use_tier(
        has_cli_rpc_or_mcp=False,
        is_web_browser_task=False,
        has_accessibility_tree=True,
        host_platform="win32",
        background_supported=False,
    )
    assert d_win_ax.tier is ComputerUseTier.L2_SEMANTIC_ACCESSIBILITY_BACKGROUND
    assert d_win_ax.transport == "orca_computer_uia_or_accessibility"
    assert d_win_ax.prefer_background is False

    d_vlm = resolve_computer_use_tier(
        has_cli_rpc_or_mcp=False,
        is_web_browser_task=False,
        has_accessibility_tree=False,
        host_platform="linux",
        background_supported=False,
    )
    assert d_vlm.tier is ComputerUseTier.L4_EVOLVING_INTERFACE_AND_VLM_FALLBACK
    assert d_vlm.distill_to_cli_if_recurring is True


@pytest.mark.parametrize("bad_bool", [1, 0, "true", "false", None, []])
def test_strict_bool_validation_rejects_non_bools(bad_bool: Any) -> None:
    with pytest.raises(ValueError, match="strict bool"):
        resolve_computer_use_tier(
            has_cli_rpc_or_mcp=bad_bool,
            is_web_browser_task=False,
            has_accessibility_tree=True,
        )
    with pytest.raises(ValueError, match="strict bool"):
        evaluate_gated_action_policy(
            action_category="orca_desktop_settings_uia",
            owner_directive_sanctioned=bad_bool,
        )


def test_invalid_host_platform_and_empty_action_category_fail_closed() -> None:
    with pytest.raises(ValueError, match="host_platform"):
        resolve_computer_use_tier(
            has_cli_rpc_or_mcp=True,
            is_web_browser_task=False,
            has_accessibility_tree=False,
            host_platform="solaris",
        )
    with pytest.raises(ValueError, match="action_category"):
        evaluate_gated_action_policy(action_category="   ")


@pytest.mark.parametrize(
    ("kwargs", "expected_token"),
    [
        ({"touches_live_capital": True}, "touches_live_capital"),
        ({"touches_secrets_or_keychain": True}, "touches_secrets_or_keychain"),
        ({"mutates_immutable_shelf": True}, "mutates_immutable_shelf"),
        ({"violates_single_active_broker_host": True}, "violates_single_active_broker_host"),
        ({"target_surface": "https://api.alpaca.markets/v2/orders"}, "api_alpaca_markets_live"),
        ({"target_surface": "http://127.0.0.1:8798/api/submit"}, "stage5_live_port_8798"),
        ({"target_surface": "127.0.0.1:4001"}, "ibkr_live_port_4001"),
        ({"target_surface": "localhost:7496"}, "ibkr_tws_live_port_7496"),
        ({"target_surface": "~/.claude/bin/live open"}, "live_window_opener"),
        ({"target_surface": "wsl --distribution sextant"}, "sextant_off_limits"),
        ({"target_surface": "macOS Keychain Dump"}, "keychain_credential_store"),
        ({"target_surface": "repo/.env.production"}, "dotenv_secret_file"),
    ],
)
def test_hard_invariants_block_even_when_owner_sanctioned(
    kwargs: dict[str, Any],
    expected_token: str,
) -> None:
    dec = evaluate_gated_action_policy(
        action_category="orca_desktop_settings_uia",
        owner_directive_sanctioned=True,
        **kwargs,
    )
    assert isinstance(dec, GatedActionDecision)
    assert dec.allowed_autonomous is False
    assert dec.permission_tier is PermissionTier.FAIL_CLOSED_HARD_INVARIANT
    assert expected_token in dec.reason


def test_human_trust_prompt_and_97bd1f5e_hook_click_surface_to_owner() -> None:
    for cat in HUMAN_TRUST_GATE_CATEGORIES:
        dec = evaluate_gated_action_policy(
            action_category=cat,
            target_surface="orca_automations_97bd1f5e_codex_hooks_trust_click",
            owner_directive_sanctioned=True,
        )
        assert dec.allowed_autonomous is False
        assert dec.permission_tier is PermissionTier.EXPLICIT_HUMAN_TRUST_GATE
        assert dec.required_surface == "owner_1click_ui"

    flag_dec = evaluate_gated_action_policy(
        action_category="orca_desktop_settings_uia",
        triggers_human_trust_prompt=True,
        owner_directive_sanctioned=True,
    )
    assert flag_dec.allowed_autonomous is False
    assert flag_dec.permission_tier is PermissionTier.EXPLICIT_HUMAN_TRUST_GATE


def test_sanctioned_zero_friction_actions_and_unclassified_default() -> None:
    for cat in SANCTIONED_ZERO_FRICTION_CATEGORIES:
        dec = evaluate_gated_action_policy(
            action_category=cat,
            target_surface="dev_environment_orca_settings",
            owner_directive_sanctioned=True,
        )
        assert dec.allowed_autonomous is True
        assert dec.permission_tier is PermissionTier.OWNER_ZERO_FRICTION_SEAMLESS

    unsanctioned = evaluate_gated_action_policy(
        action_category="orca_desktop_settings_uia",
        owner_directive_sanctioned=False,
    )
    assert unsanctioned.allowed_autonomous is False
    assert unsanctioned.permission_tier is PermissionTier.EXPLICIT_HUMAN_TRUST_GATE

    unclassified = evaluate_gated_action_policy(
        action_category="unknown_experimental_action",
        owner_directive_sanctioned=True,
    )
    assert unclassified.allowed_autonomous is False
    assert unclassified.permission_tier is PermissionTier.EXPLICIT_HUMAN_TRUST_GATE
    assert unclassified.reason == "unclassified_action_requires_owner_review"


def test_computer_use_manifest_completeness() -> None:
    manifest = build_computer_use_manifest()
    assert manifest["adr"] == "ADR-0042"
    assert manifest["schemaVersion"] == COMPUTER_USE_SCHEMA_VERSION
    escalation = manifest["escalationOrder"]
    tiers = manifest["permissionTiers"]
    assert isinstance(escalation, list) and len(escalation) == 4
    assert isinstance(tiers, list) and len(tiers) == 3
    stack = UPSTREAM_COMPUTER_USE_REFERENCE_STACK
    for required_repo in (
        "simular-ai/Agent-S",
        "trycua/cua",
        "microsoft/UFO",
        "bytedance/UI-TARS-desktop",
        "xlang-ai/OpenCUA",
        "HKUDS/CLI-Anything",
        "mediar-ai/terminator",
        "steipete/peekaboo",
        "vercel-labs/agent-browser",
        "microsoft/playwright-mcp",
        "e2b-dev/desktop",
        "bytebot-ai/bytebot",
        "openclaw/openclaw",
        "xlang-ai/OSWorld-V2",
        "X-PLUG/OSWorld-MCP",
    ):
        assert required_repo in stack
