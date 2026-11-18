# ADR-0008: L7 Context Compression, Dolt Task Graph & Cross-Peer SQLite WAL Memory Bus

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L7` Context Efficiency & Cross-Session / Cross-Peer Memory
- **Evidence Grade:** E3 (Live SQLite WAL & Dolt Verified)
- **Revisit Trigger:** 2027-01-01 or cost-per-accepted-solve regression

## Context and Problem Statement

Backtest sweeps, test logs, and Parquet inspections rapidly flood context windows, while concurrent sessions across Claude Code, Antigravity (`AGY`), Codex, and DeepSeek Harness (`DSH`) risk stepping on each other's files or losing root-cause lessons and pre-registered hypothesis hashes.

## Decision Outcome

1. **Tool-Output FTS5 Sandbox (`mksglu/context-mode` `v2.2.1` @ `99c5f38b622c918a9a2abfe8a263a2737623e21b`):** Keeps large tool outputs outside the prompt window in local SQLite FTS5 (`BM25+RRF`), upgrading the previously held `v1.0.169` release to `v2.2.1` (released `2026-11-17`).
2. **Cross-Peer SQLite WAL Bus (`sota-peer-bus` MCP + `~/.agents/wiki/`):** Wire `~/.gemini/config/plugins/sota-peer-memory-and-council/mcp/peer_bus_mcp.py` into `.mcp.json` and symlink shared `~/.agents/skills/*` so Claude Code, AGY, Codex, and Orca workers share one transactional lease table (`ACTIVE_PEERS.md`), handover log (`HANDOVER.md`), root-cause ledger (`LESSONS.md`), and immutable SHA-256 hypothesis pre-registration table (`HYPOTHESIS_LEDGER.md`).
3. **Dependency-Aware Task Memory (`gastownhall/beads` `v1.3.4`):** Initialized local embedded Dolt database (`cch` prefix, `.git/info/exclude`, `bd metrics off`) for multi-step issue graphs.
4. **Semantic Recall & Owner Study Layer:** Retains local `OpenViking` (`~/.local/bin/openviking`) and `amosblomqvist/learnharness` (`v0.6.1`) without cloud telemetry.

## Alternatives Considered

- **`rtk-ai/rtk` (86.9k★) & `headroomlabs-ai/headroom` (79.9k★) as default shell proxies:** Held as optional A/B candidates per `northstar` ADR-0069 (lossy CLI rewriting can obscure exact pytest/traceback line numbers unless queried via FTS5 like `context-mode`).
- **`thedotmack/claude-mem` (117.9k★):** Kept out of default enabled plugins to avoid running a second competing memory-capture daemon alongside `sota-peer-bus` + `beads` + `context-mode`.

## Verification Witness

- `~/.agents/bin/sota-bus status --repo cc-sota-harness` and JSON-RPC `tools/list` on `sota-peer-bus` MCP (`6` tools).
