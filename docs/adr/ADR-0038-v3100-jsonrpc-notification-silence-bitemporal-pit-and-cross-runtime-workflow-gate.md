# ADR-0038: `v3.10.0` Open-Core JSON-RPC Notification Silence, Bitemporal PIT Monotonicity & Cross-Runtime Workflow Gate

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L1 / L3 / L4 / L8 / L10 (`P0–P5` × `T1–T5` × `H0–H7`)
- **Evidence Grade:** E4 (`38` ADRs, `pytest` + Hypothesis Verified, JSON-RPC 2.0 Notification Silence & `DF1..DF12` Bitemporal Monotonicity)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/sota-multi-model-workflows, https://github.com/databento/databento-python, https://github.com/stablyai/orca
- **Revisit Trigger:** Ecosystem `v4.0.0` promotion or `2026-12-06` `23/5` Consolidated SIP cutover

## Context and Problem Statement

1. **JSON-RPC 2.0 Notification Silence:** MCP clients emit `notifications/initialized` without an `id` (or with `id: null`). Emitting a response breaks strict stdio MCP transport framing across `Antigravity`, `Claude Code`, `Codex`, `OpenCode`, `Pi/OMP`, and `DSH`.
2. **Bitemporal `DF1..DF12` Causal Ordering:** Strategy ranking handoffs must prove `ts_event_ns <= ts_recv_ns <= decision_ns` prior to consuming finalized `12`-Feed Symbol Ranking inputs.

## Decision Outcome

1. **Publish `validate_mcp_jsonrpc_notification_frame()` & `validate_bitemporal_pit_ordering()` in `src/cc_sota_harness/workstation_lane.py`:**
   - Provide reusable open-core validators enforcing `0`-reply JSON-RPC notification hygiene and monotonic nanosecond bitemporal PIT invariants alongside `sota-multi-model-workflows` (`ADR-0024`).

## Alternatives Considered

- **Returning JSON-RPC error objects with `"id": null` on notifications:** Rejected — violates JSON-RPC 2.0 Section 4.1 notification semantics and triggers client transport resets.

## Verification Witness

- `python scripts/architecture_catalog.py --write && python scripts/architecture_catalog.py --check` (`38` ADRs valid, `0` drift)
- `ruff check . && pytest -q` & `gitleaks protect --staged --no-banner` (`0` leaks)
