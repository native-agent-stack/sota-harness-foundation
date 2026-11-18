# ADR-0011: L10 Local-Only Observability, Statusline HUD & Zero-Telemetry Archive

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L10` Observability, HUD & Session Accounting
- **Evidence Grade:** E2 (Installed & Zero-Telemetry Configured)
- **Revisit Trigger:** 2027-01-01 or OpenTelemetry GenAI schema stabilization

## Context and Problem Statement

Multi-agent orchestration across Claude Code, OMC subagents, and Codex workers requires real-time visibility into context-window saturation, active tools, rate-limit pace, and historical token burn — without leaking prompts, code, or account identifiers to external cloud telemetry endpoints.

## Decision Outcome

1. **Real-Time Lead HUD (`jarrodwatts/claude-hud` `v0.15.0` @ `b86e1c3e5255880578de4b7cc87dc383228c2a18`):** Local-only statusline rendering context usage, active tools, running subagents, and rate-limit pace alongside `~/.claude/canon/statusline.sh`.
2. **Cross-Agent Local SQLite Archive (`kenn-io/agentsview` `v0.47.0`):** Locked in `mise.toml` with `DO_NOT_TRACK=1`, `AGENTSVIEW_TELEMETRY_ENABLED=0`, and `AGENTSVIEW_NO_DAEMON=1` enforced in `.claude/settings.json`.
3. **On-Demand Session Impact Reports:** `session-report@claude-plugins-official` and `receipts@claude-plugins-official` (`@ fd30cee3ecd5`) generate local-only session summaries with zero background hooks.
4. **Local OTLP Collector Binary:** Retains host `open-telemetry/opentelemetry-collector-releases` (`0.165.0`) on loopback (`127.0.0.1`) with prompt/tool-body logging disabled.

## Alternatives Considered

- **Cloud-hosted SaaS tracing (`LangSmith`, `Helicone` Cloud, `PostHog` Cloud):** Rejected; no prompt, code, or trading artifact leaves this machine.

## Verification Witness

- `doctor.py` verifies `claude-hud@claude-hud`, `agentsview`, `session-report`, `receipts`, and zero-telemetry environment keys.
