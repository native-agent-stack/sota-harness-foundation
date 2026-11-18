# ADR-0007: L5–L6 Structural Code Intelligence, Upstream Shelf FTS5 & Institutional Quant Skills

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L5` Code Intelligence & `L6` Live Docs / Quantitative Skills
- **Evidence Grade:** E3 (Indexed & MCP-Verified)
- **Revisit Trigger:** 2027-01-01 or upstream shelf pin bump

## Context and Problem Statement

Grep-and-whole-file reading wastes context tokens and misses call-graph blast radius across Python/Rust/TypeScript repositories, while unpinned LLM recollection hallucinates `nautilus_trader`, `alpaca-py`, `polars`, and `skfolio` APIs.

## Decision Outcome

1. **Official Language Servers (`anthropics/claude-plugins-official` @ `fd30cee3ecd5a8ee772733c5d20c0f2bae2da2f0`):** Enable `pyright-lsp`, `rust-analyzer-lsp`, and `typescript-lsp` (`pyproject.toml` `[tool.pyright]` bound to `.venv` for zero-config symbol resolution).
2. **Persistent AST & Call-Graph MCP (`DeusData/codebase-memory-mcp` `v0.12.1` @ `e6980cd60bfbf0a3591dd63b6d4ff010a8f6b2f8` + `@colbymchenry/codegraph` `1.6.3`):** Wire `codebase-memory` in `.mcp.json` (2,822 nodes, 5,288 edges indexed) and initialize `.codegraph/` (`--local-only`, telemetry disabled, 741 nodes, 2,838 edges).
3. **18-Repo Upstream Shelf FTS5 & AST Search (`agy-sota-core` MCP):** Wire `~/.gemini/config/plugins/agy-sota-core/mcp/sota_core_mcp.py` in `.mcp.json` so Claude Code queries all 18 pinned `~/Documents/upstream/` clones (`sota_shelf_search`, `sota_symbol_lookup`, `sota_ast_search`) directly over stdio MCP.
4. **Live Docs & Institutional Quant/Finance Skills:** Enable `context7@claude-plugins-official`, `anthropics/financial-services` (`equity-research`, `financial-analysis`, `market-researcher` @ `3e32c2287dcb`), and 7 pinned `K-Dense-AI/scientific-agent-skills` (`polars`, `statsmodels`, `statistical-analysis`, `hypothesis-generation`, `exploratory-data-analysis`, `scikit-learn`, `aeon` @ `ec59a29a03d5`).

## Alternatives Considered

- **`abhigyanpatwari/GitNexus` (48.6k★):** PolyForm Noncommercial license and mutates `AGENTS.md`/`CLAUDE.md` unless `--index-only`; rejected in favor of MIT-licensed `codebase-memory-mcp` and `codegraph`.
- **`zilliztech/claude-context` (12.6k★):** Requires external Milvus + embedding API keys; rejected in favor of local zero-key AST + FTS5 indexing.

## Verification Witness

- `doctor.py` verifies stdio JSON-RPC `initialize` + `tools/list` on `codebase-memory` and `agy-sota-core` plus SHA integrity of allvendored skills.
