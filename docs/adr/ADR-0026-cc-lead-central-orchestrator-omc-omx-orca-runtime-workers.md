# ADR-0026: Claude Code (`cc-lead`) Central Multi-Session Orchestrator & 5-Channel Runtime Worker Hub (`v3.5.0`)

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L1 / L3 / L4 / L7 / L8 (`P0–P5` × `T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** `oh-my-claudecode` (`OMC`) major runtime bump (`>= v6.0`), `stablyai/orca` orchestration schema change, or Artificial Analysis v5.x frontier shift

## Context and Problem Statement

Following `ADR-0025` (`sota-workstation v2.0.0` hardened headless `orca serve` and lease-safe dual-workstation co-op), operating heterogeneous frontier runtimes (`claude`, `omc`, `codex`, `omx`, `orca`, `agy`/`gemini`, `opencode`/`oh-my-openagent`, `dsh`, `pi`/`omp`, `goose`, `hcom`) across concurrent multi-session tasks required a single sovereign command hub so Claude Code (`cc-lead`, `claude-fable-5-2` `xhigh`) directs every worker runtime without violating `oneModelPerConversation`, `Hephaestus` non-GPT routing, isolated git worktrees, or `sota-bus` path-glob lease disjointness.

## Decision Outcome

We formalize `config/multi-model-routing.json` (`v1.1.0`) paired with `sota-cc-hub` (`sota-multi-model-workflows` `src/sota_mmw/cc_lead_hub.py` & Workflow `#14` `cc_lead_multi_runtime_workers_workflow.py` `@ 3312afa5aa92`):

1. **Claude Code (`cc-lead`) Sovereign Central Orchestrator (`oneModelPerConversation = true`):**
   - `cc-lead` stays pinned to `claude-fable-5-2` (`effortLevel = xhigh`, `600k` auto-compact window) so prompt-cache prefixes never invalidate mid-conversation, delegating multi-vendor execution strictly across isolated child processes and worktrees with `OMC_RUNTIME_V2=1` and `OMC_TEAM_WORKTREE_MODE=branch`.
2. **Five Deterministic Runtime Worker Channels:**
   - **Channel 1 (`omc ultragoal` + `/goal`):** Durable `.omc/ultragoal/plans/<id>/` goal ledgers (`omc ultragoal create-goals --json`) paired with native `/goal` Stop-hook verification.
   - **Channel 2 (`omc team` & `omc interop`):** Parallel branch-worktree worker teams (`omc team "<N:agent:role,...>" --no-decompose`) and split-pane `Claude OMC <-> Codex OMX` (`gpt-6.2-astra` / `gpt-6.2-sol`) interop.
   - **Channel 3 (`omc ask` & `omx exec` / `omx mission`):** Ephemeral cross-family second-opinion/falsifier briefs (`codex`, `antigravity`, `muse`, `grok`) enforcing `>= 3` concrete frontier vendors (`anthropic`, `openai`, `google`) on every Stage-3+ plan.
   - **Channel 4 (`stablyai/orca` Supervised Child Worktrees):** Reactive `orca orchestration worker-start --worktree new-child --repo id:<uuid>` across portable `Mac M5 Max` (`local`) and stationary `Noesis` (`100.110.115.22`, `64c / 128 GB / RTX 4090`) using push `worker_done` / `send` / `gate-create` (`0` polling loops).
   - **Channel 5 (`OMO`, `DSH`, `Pi/OMP`, `Goose`, `hcom` & `sota-bus`):** Non-GPT `Hephaestus` (`kimi-k3.1-pro` via `opencode` / `oh-my-openagent`), `deepseek-v4-pro` pre-wall (`<= 2026-10-15`) sweeps via `dsh`, `hcom` cross-terminal push, and comma/glob-aware `sota-bus` lease collision guards.

## Alternatives Considered

1. **Hot-swap frontier models inside a single Claude Code conversation via mid-turn proxy rewriting:** Rejected — destroys Anthropic prompt-cache prefixes and blurs attribution across model families (`oneModelPerConversation = true`).
2. **Allow mutating multi-runtime workers on shared primary checkouts:** Rejected — causes index/HEAD races across concurrent peer sessions; mutating workers require isolated child git worktrees plus disjoint `sota-bus` path leases.

## Verification Witness

- `python3 scripts/runtime_fleet.py` (`PASS`, `28` runtimes & `11` frontier models verified), `python3 scripts/architecture_catalog.py --check` (`26 ADRs valid, 0 drift`), `ruff`, `ty@0.0.104`, `pytest`, and `gitleaks --no-git` (`0` leaks).
- Live `run_workflow` receipt on `cc_lead_multi_runtime_workers_workflow.py` (`plan_sha256 = 678fc0cf289b00fd85f7e23a7b5c300b1284fbd1f60c0abe62a9280a0524a5d7`, `15/15` hub binaries, `sota-doctor` `12/12 PASS`, GitHub Actions Run `44240198191` `SUCCESS`).
