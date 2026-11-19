# ADR-0042: `v3.10.7` Agent-Native 5-Layer Hybrid Computer-Use Stack & Tiered Zero-Friction Permission Policy

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0 / L1 / L2 / L5 / L7 / L8 (`H1–H3` × Dual-Machine `Portable Mac M5 Max <-> Stationary Noesis` Computer-Use & Gated-Action Governance)
- **Evidence Grade:** E4 (`42` ADRs, `src/cc_sota_harness/computer_use_contract.py`, `tests/test_computer_use_contract.py`, live `orca computer capabilities` telemetry on `darwin` & `win32`, `pytest` + `ruff` + `gitleaks` `0` Leaks)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/simular-ai/Agent-S, https://github.com/trycua/cua, https://github.com/microsoft/UFO, https://github.com/bytedance/UI-TARS-desktop, https://github.com/xlang-ai/OpenCUA, https://github.com/HKUDS/CLI-Anything, https://github.com/mediar-ai/terminator, https://github.com/steipete/peekaboo, https://github.com/vercel-labs/agent-browser, https://github.com/microsoft/playwright-mcp, https://github.com/e2b-dev/desktop, https://github.com/bytebot-ai/bytebot, https://github.com/openclaw/openclaw, https://github.com/xlang-ai/OSWorld-V2, https://github.com/X-PLUG/OSWorld-MCP
- **Revisit Trigger:** `2026-12-06` `23/5` Consolidated SIP cutover or upgrade of `orca computer` / `Agent-S` S4 runtime bindings

## Context and Problem Statement

Recent dual-machine convergence (`Portable Mac M5 Max` <-> `Stationary Noesis` Win32/WSL2) showed two opposite failure modes when autonomous agents operate workstation settings, Orca workspaces, and cross-runtime toolchains:
1. **Pure GUI / Terminal-Spawn Friction:** Spawning interactive terminals or using raw screenshot-and-click loops burns context tokens, steals window focus, and suffers UI flakiness. At the same time, verified 2026 computer-use research (`simular-ai/Agent-S` S4 evolving interfaces, `CoAct-1`, `X-PLUG/OSWorld-MCP`, `microsoft/UFO` UFO2/UFO3, `trycua/cua`, `HKUDS/CLI-Anything`, `mediar-ai/terminator`, `steipete/peekaboo`, `vercel-labs/agent-browser`) proves that hybrid **CLI/RPC/MCP + OS Accessibility Trees + Compact Browser CDP Refs** outperforms pixel-only CUA on both latency and `OSWorld-V2` reliability.
2. **Permission Ambiguity on Gated Actions:** Unbounded prompt-spam slows down owner-authorized Orca configuration, multi-runtime permission alignment, and paper-lane convergence, whereas blindly auto-approving everything would endanger fail-closed live-capital, credential, immutable-shelf, and explicit platform-trust boundaries.

## Decision Outcome

1. **Adopt the Canonical 5-Layer Hybrid Computer-Use Escalation Ladder (`resolve_computer_use_tier` in `src/cc_sota_harness/computer_use_contract.py`):**
   - **L1 — Programmatic CLI / `:8792` Zero-Terminal RPC / MCP (`CLI-Anything`, `sota-workstation`, `sota-bus`, `hcom`, `openclaw`):** Mandatory first choice whenever a documented CLI, JSON RPC, or MCP interface exists (zero pixel tax, deterministic outputs).
   - **L2 — Semantic OS Accessibility & Background UIA (`orca computer`, `trycua/cua` / Lume, `microsoft/UFO`, `mediar-ai/terminator`, `steipete/peekaboo`):** Second choice for native desktop apps/settings, preferring `input.background=true` on `darwin` (`orca-computer-use-macos`) and non-disruptive UIA (`orca-computer-use-windows`) on `win32`.
   - **L3 — Compact Browser CDP Refs (`orca browser`, `vercel-labs/agent-browser`, `microsoft/playwright-mcp`):** Used for web workflows via compact `@eN` accessibility/DOM snapshots instead of raw desktop screenshots.
   - **L4 — `Agent-S` S4 Trajectory-to-CLI Distillation & VLM Fallback (`UI-TARS-2`, `OpenCUA`, `e2b-dev/desktop`, `bytebot`):** Visual pixel CUA is restricted to unexposed canvas/UI surfaces; any recurring manual/GUI sequence must be distilled into idempotent CLI/config scripts (`sync-all-8-runtimes.py`, `sync_runtime_hygiene.py`).
2. **Enforce Three-Tier Gated-Action Permission Governance (`evaluate_gated_action_policy`):**
   - **`OWNER_ZERO_FRICTION_SEAMLESS`:** Autonomous zero-friction execution across documented native configs/CLIs/RPC/UIA for owner-sanctioned non-destructive work (`orca_desktop_settings_uia`, `runtime_hygiene_sync`, `multi_runtime_permission_config`, `zero_terminal_coop_rpc`, `repo_adr_and_test_convergence`, `paper_lane_operation`, `browser_compact_ref_automation`).
   - **`EXPLICIT_HUMAN_TRUST_GATE`:** Platform/OS trust dialogs (e.g., Orca `97bd1f5e` hooks trust click, OS TCC/admin elevation, CAPTCHAs, or unclassified actions) are surfaced cleanly for 1-click owner confirmation and are never bypassed.
   - **`FAIL_CLOSED_HARD_INVARIANT`:** Live-capital endpoints (`api.alpaca.markets`, `:8798`, `:4001`, `:7496`, `.claude/bin/live`), credentials/Keychain/`.env`, immutable `~/Documents/upstream/` & closed repos, `sextant`, and `singleActiveBrokerHostOnly=true` breaches fail closed unconditionally regardless of `owner_directive_sanctioned`.

## Alternatives Considered

- **Pure VLM Screenshot-Clicking (`L4` Default):** Rejected — high token cost, cursor hijacking, and brittle visual coordinates (`OSWorld-V2` demonstrates programmatic/hybrid superiority).
- **Blanket Auto-Approval for All Prompts:** Rejected — violates Stage-5 Live firewall, credential hygiene, and platform human-trust boundaries.

## Verification Witness

- `uv run python scripts/architecture_catalog.py && uv run python scripts/architecture_catalog.py --check` (`42 ADRs valid, 0 drift`).
- `uv run pytest -q && ruff check . && ruff format --check . && gitleaks detect --source . --no-git --no-banner` (`PASS`, `0` leaks).
