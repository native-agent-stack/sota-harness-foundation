"""Agent-Native 5-Layer Hybrid Computer-Use & Tiered Zero-Friction Permission Contract (`ADR-0042`).

Distills verified 2026 SOTA computer-use architectures (`simular-ai/Agent-S` S4 evolving interfaces,
`trycua/cua` cross-OS/Lume sandboxes & accessibility drivers, `microsoft/UFO` UFO2/UFO3 GUI+OS-API
DAGs, `bytedance/UI-TARS-desktop`, `HKUDS/CLI-Anything`, `mediar-ai/terminator`, `steipete/peekaboo`,
`vercel-labs/agent-browser`, `microsoft/playwright-mcp`, `openclaw/openclaw`, `xlang-ai/OSWorld-V2`,
`X-PLUG/OSWorld-MCP`) into an executable routing and permission-tier contract for our dual-machine
(`Portable Mac M5 Max <-> Stationary Noesis`) ecosystem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

COMPUTER_USE_SCHEMA_VERSION = "sota-computer-use-5layer.v1.0"

VALID_HOST_PLATFORMS: frozenset[str] = frozenset({"darwin", "win32", "linux"})

SANCTIONED_ZERO_FRICTION_CATEGORIES: frozenset[str] = frozenset(
    {
        "orca_desktop_settings_uia",
        "runtime_hygiene_sync",
        "multi_runtime_permission_config",
        "zero_terminal_coop_rpc",
        "repo_adr_and_test_convergence",
        "paper_lane_operation",
        "browser_compact_ref_automation",
    }
)

HUMAN_TRUST_GATE_CATEGORIES: frozenset[str] = frozenset(
    {
        "platform_trust_prompt",
        "plugin_or_hook_trust_click",
        "os_tcc_or_admin_elevation",
        "captcha_or_antibot",
    }
)

_FORBIDDEN_SURFACE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api_alpaca_markets_live", re.compile(r"(?<![a-z0-9\-])api\.alpaca\.markets\b")),
    ("stage5_live_port_8798", re.compile(r"(?:^|[:/\s=])8798(?=$|[:/\s,])")),
    ("ibkr_live_port_4001", re.compile(r"(?:^|[:/\s=])4001(?=$|[:/\s,])")),
    ("ibkr_tws_live_port_7496", re.compile(r"(?:^|[:/\s=])7496(?=$|[:/\s,])")),
    ("live_window_opener", re.compile(r"\.claude/bin/live\b")),
    ("sextant_off_limits", re.compile(r"\bsextant\b")),
    ("keychain_credential_store", re.compile(r"\bkeychain\b")),
    ("dotenv_secret_file", re.compile(r"(?:^|[/\\\s:=])\.env(?=$|[/\\\s.]|\b)")),
)

UPSTREAM_COMPUTER_USE_REFERENCE_STACK: dict[str, dict[str, str]] = {
    "simular-ai/Agent-S": {
        "url": "https://github.com/simular-ai/Agent-S",
        "role": "Modular planner/grounding split + Agent-S S4 evolving agent interfaces (trajectory-to-CLI distillation)",
    },
    "trycua/cua": {
        "url": "https://github.com/trycua/cua",
        "role": "Cross-OS sandbox infra, Apple Silicon Lume VMs, accessibility tree drivers, background delivery & MCP",
    },
    "microsoft/UFO": {
        "url": "https://github.com/microsoft/UFO",
        "role": "UFO2 Desktop AgentOS (Win32 UIA/WinCOM hybrid + PiP virtual desktop) & UFO3 cross-device Task Constellation DAGs",
    },
    "bytedance/UI-TARS-desktop": {
        "url": "https://github.com/bytedance/UI-TARS-desktop",
        "role": "Native System-2 GUI VLM stack (UI-TARS-2) + desktop/CLI/MCP operators across macOS, Windows, Linux & Android",
    },
    "xlang-ai/OpenCUA": {
        "url": "https://github.com/xlang-ai/OpenCUA",
        "role": "Open foundation CUA data pipelines & open-weight grounding models evaluated on OSWorld-Verified",
    },
    "HKUDS/CLI-Anything": {
        "url": "https://github.com/HKUDS/CLI-Anything",
        "role": "Auto-generated stateful JSON-output CLI harnesses converting GUI software into deterministic agent-native tools",
    },
    "mediar-ai/terminator": {
        "url": "https://github.com/mediar-ai/terminator",
        "role": "Rust Playwright-for-desktop accessibility automation (strongest on Windows UIA, focus-preserving + MCP)",
    },
    "steipete/peekaboo": {
        "url": "https://github.com/steipete/peekaboo",
        "role": "Native Swift macOS Accessibility API CLI & MCP server for low-token non-disruptive local desktop control",
    },
    "vercel-labs/agent-browser": {
        "url": "https://github.com/vercel-labs/agent-browser",
        "role": "Rust CDP daemon emitting ultra-compact accessibility element refs (@e1) over CLI/stdio MCP",
    },
    "microsoft/playwright-mcp": {
        "url": "https://github.com/microsoft/playwright-mcp",
        "role": "Official cross-browser MCP bridge & playwright-cli skill-guided deterministic browser automation",
    },
    "e2b-dev/desktop": {
        "url": "https://github.com/e2b-dev/desktop",
        "role": "Ephemeral Firecracker microVM Linux desktop sandboxes (~150ms boot) for parallel isolated CUA runs",
    },
    "bytebot-ai/bytebot": {
        "url": "https://github.com/bytebot-ai/bytebot",
        "role": "Self-hosted persistent containerized Linux desktop environment for long-running autonomous tasks",
    },
    "openclaw/openclaw": {
        "url": "https://github.com/openclaw/openclaw",
        "role": "Local-first autonomous goal gateway orchestrating async cron/subagent loops with deterministic CLI/MCP tools",
    },
    "xlang-ai/OSWorld-V2": {
        "url": "https://github.com/xlang-ai/OSWorld-V2",
        "role": "Strict binary long-horizon desktop workflow benchmark separating real reliability from saturated V1 suites",
    },
    "X-PLUG/OSWorld-MCP": {
        "url": "https://github.com/X-PLUG/OSWorld-MCP",
        "role": "Hybrid GUI + MCP tool invocation benchmark proving structured tool calls beat pure pixel clicking",
    },
}


class ComputerUseTier(StrEnum):
    """Canonical escalation ladder from zero-pixel-tax native control to VLM fallback."""

    L1_PROGRAMMATIC_CLI_RPC_MCP = "L1_PROGRAMMATIC_CLI_RPC_MCP"
    L2_SEMANTIC_ACCESSIBILITY_BACKGROUND = "L2_SEMANTIC_ACCESSIBILITY_BACKGROUND"
    L3_COMPACT_BROWSER_CDP_REFS = "L3_COMPACT_BROWSER_CDP_REFS"
    L4_EVOLVING_INTERFACE_AND_VLM_FALLBACK = "L4_EVOLVING_INTERFACE_AND_VLM_FALLBACK"


class PermissionTier(StrEnum):
    """Three-tier permission governance preserving owner velocity and fail-closed invariants."""

    OWNER_ZERO_FRICTION_SEAMLESS = "OWNER_ZERO_FRICTION_SEAMLESS"
    EXPLICIT_HUMAN_TRUST_GATE = "EXPLICIT_HUMAN_TRUST_GATE"
    FAIL_CLOSED_HARD_INVARIANT = "FAIL_CLOSED_HARD_INVARIANT"


@dataclass(frozen=True)
class ComputerUseRouteDecision:
    """Deterministic routing outcome for a computer-use / workstation action."""

    tier: ComputerUseTier
    transport: str
    prefer_background: bool
    distill_to_cli_if_recurring: bool
    rationale: str


@dataclass(frozen=True)
class GatedActionDecision:
    """Fail-closed permission verdict for an agent-proposed gated or workstation action."""

    allowed_autonomous: bool
    permission_tier: PermissionTier
    reason: str
    required_surface: str


def _require_strict_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a strict bool, got {type(value).__name__}")
    return value


def _require_non_empty_str(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty str")
    return value.strip()


def resolve_computer_use_tier(
    *,
    has_cli_rpc_or_mcp: bool,
    is_web_browser_task: bool,
    has_accessibility_tree: bool,
    host_platform: str = "darwin",
    background_supported: bool = False,
) -> ComputerUseRouteDecision:
    """Select the lowest-friction, highest-determinism SOTA computer-use tier."""
    cli_ok = _require_strict_bool("has_cli_rpc_or_mcp", has_cli_rpc_or_mcp)
    web_ok = _require_strict_bool("is_web_browser_task", is_web_browser_task)
    ax_ok = _require_strict_bool("has_accessibility_tree", has_accessibility_tree)
    bg_ok = _require_strict_bool("background_supported", background_supported)
    plat = _require_non_empty_str("host_platform", host_platform).lower()
    if plat not in VALID_HOST_PLATFORMS:
        raise ValueError(f"host_platform must be one of {sorted(VALID_HOST_PLATFORMS)}, got {plat!r}")

    if cli_ok:
        return ComputerUseRouteDecision(
            tier=ComputerUseTier.L1_PROGRAMMATIC_CLI_RPC_MCP,
            transport="cli_or_zero_terminal_rpc_or_mcp",
            prefer_background=True,
            distill_to_cli_if_recurring=False,
            rationale="Programmatic CLI, :8792 zero-terminal RPC, or MCP achieves zero pixel tax and deterministic execution.",
        )

    if web_ok:
        return ComputerUseRouteDecision(
            tier=ComputerUseTier.L3_COMPACT_BROWSER_CDP_REFS,
            transport="orca_browser_or_agent_browser_or_playwright_cli",
            prefer_background=True,
            distill_to_cli_if_recurring=False,
            rationale="Web workflows use compact accessibility/CDP element refs (@eN) instead of raw desktop screenshots.",
        )

    if ax_ok:
        if plat == "darwin" and bg_ok:
            transport = "orca_computer_macos_background"
        else:
            transport = "orca_computer_uia_or_accessibility"
        return ComputerUseRouteDecision(
            tier=ComputerUseTier.L2_SEMANTIC_ACCESSIBILITY_BACKGROUND,
            transport=transport,
            prefer_background=bg_ok,
            distill_to_cli_if_recurring=True,
            rationale="Semantic accessibility / UIA control avoids pixel guessing and preserves focus when supported.",
        )

    return ComputerUseRouteDecision(
        tier=ComputerUseTier.L4_EVOLVING_INTERFACE_AND_VLM_FALLBACK,
        transport="agent_s_evolving_interface_or_vlm_fallback",
        prefer_background=bg_ok,
        distill_to_cli_if_recurring=True,
        rationale="Fallback to visual CUA only for unexposed UI surfaces; distill recurring sequences into CLI/config scripts.",
    )


def evaluate_gated_action_policy(
    *,
    action_category: str,
    target_surface: str = "",
    touches_live_capital: bool = False,
    touches_secrets_or_keychain: bool = False,
    mutates_immutable_shelf: bool = False,
    triggers_human_trust_prompt: bool = False,
    violates_single_active_broker_host: bool = False,
    owner_directive_sanctioned: bool = False,
) -> GatedActionDecision:
    """Evaluate an action against fail-closed invariants, explicit human gates, and zero-friction tiers."""
    cat = _require_non_empty_str("action_category", action_category).lower()
    if not isinstance(target_surface, str):
        raise ValueError(f"target_surface must be a str, got {type(target_surface).__name__}")
    surf = target_surface.strip().lower()

    live = _require_strict_bool("touches_live_capital", touches_live_capital)
    secrets = _require_strict_bool("touches_secrets_or_keychain", touches_secrets_or_keychain)
    shelf = _require_strict_bool("mutates_immutable_shelf", mutates_immutable_shelf)
    trust_prompt = _require_strict_bool("triggers_human_trust_prompt", triggers_human_trust_prompt)
    split_brain = _require_strict_bool("violates_single_active_broker_host", violates_single_active_broker_host)
    sanctioned = _require_strict_bool("owner_directive_sanctioned", owner_directive_sanctioned)

    # Tier 3 (highest priority): Hard invariants fail closed regardless of owner_directive_sanctioned.
    matched_surface = next((label for label, rx in _FORBIDDEN_SURFACE_PATTERNS if rx.search(surf)), "")
    if live or secrets or shelf or split_brain or matched_surface:
        reasons: list[str] = []
        if live:
            reasons.append("touches_live_capital")
        if secrets:
            reasons.append("touches_secrets_or_keychain")
        if shelf:
            reasons.append("mutates_immutable_shelf")
        if split_brain:
            reasons.append("violates_single_active_broker_host")
        if matched_surface:
            reasons.append(f"forbidden_target_surface:{matched_surface}")
        return GatedActionDecision(
            allowed_autonomous=False,
            permission_tier=PermissionTier.FAIL_CLOSED_HARD_INVARIANT,
            reason=f"Blocked by fail-closed hard invariant ({', '.join(reasons)})",
            required_surface="blocked_hard_invariant",
        )

    # Tier 2: Explicit human trust gates must be surfaced cleanly, never bypassed.
    if trust_prompt or cat in HUMAN_TRUST_GATE_CATEGORIES:
        return GatedActionDecision(
            allowed_autonomous=False,
            permission_tier=PermissionTier.EXPLICIT_HUMAN_TRUST_GATE,
            reason="Explicit platform/OS human trust gate must be surfaced cleanly to owner, never bypassed",
            required_surface="owner_1click_ui",
        )

    # Tier 1: Owner-sanctioned zero-friction execution across documented native config/CLI/RPC/UIA flows.
    if sanctioned and cat in SANCTIONED_ZERO_FRICTION_CATEGORIES:
        return GatedActionDecision(
            allowed_autonomous=True,
            permission_tier=PermissionTier.OWNER_ZERO_FRICTION_SEAMLESS,
            reason=f"Owner-sanctioned zero-friction execution permitted via documented native config/CLI/RPC ({cat})",
            required_surface="autonomous_native_config_cli_rpc",
        )

    # Default fail-closed fallback for unclassified or unsanctioned actions.
    return GatedActionDecision(
        allowed_autonomous=False,
        permission_tier=PermissionTier.EXPLICIT_HUMAN_TRUST_GATE,
        reason="unclassified_action_requires_owner_review",
        required_surface="owner_review",
    )


def build_computer_use_manifest() -> dict[str, object]:
    """Build deterministic manifest summarizing the ADR-0042 5-layer computer-use & permission contract."""
    return {
        "adr": "ADR-0042",
        "schemaVersion": COMPUTER_USE_SCHEMA_VERSION,
        "escalationOrder": [
            ComputerUseTier.L1_PROGRAMMATIC_CLI_RPC_MCP.value,
            ComputerUseTier.L2_SEMANTIC_ACCESSIBILITY_BACKGROUND.value,
            ComputerUseTier.L3_COMPACT_BROWSER_CDP_REFS.value,
            ComputerUseTier.L4_EVOLVING_INTERFACE_AND_VLM_FALLBACK.value,
        ],
        "permissionTiers": [
            PermissionTier.OWNER_ZERO_FRICTION_SEAMLESS.value,
            PermissionTier.EXPLICIT_HUMAN_TRUST_GATE.value,
            PermissionTier.FAIL_CLOSED_HARD_INVARIANT.value,
        ],
        "sanctionedZeroFrictionCategories": sorted(SANCTIONED_ZERO_FRICTION_CATEGORIES),
        "humanTrustGateCategories": sorted(HUMAN_TRUST_GATE_CATEGORIES),
        "upstreamReferenceStack": UPSTREAM_COMPUTER_USE_REFERENCE_STACK,
    }
