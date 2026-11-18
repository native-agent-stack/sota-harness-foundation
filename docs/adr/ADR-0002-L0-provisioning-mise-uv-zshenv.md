# ADR-0002: L0 Reproducible Provisioning & Host PATH Spine (`mise` + `uv` + `~/.zshenv`)

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** `L0` Provisioning & Polyglot Toolchain
- **Evidence Grade:** E3 (174 Lock Targets Verified)
- **Revisit Trigger:** 2027-01-01 or new `mise` / `uv` / CPython minor baseline

## Context and Problem Statement

On macOS without Homebrew, interactive terminals read `~/.zshrc`, whereas non-interactive subshells spawned by Orca prechecks, Claude Code `PreToolUse` hooks, Git hooks, and stdio MCP servers only read `~/.zshenv`. Missing `~/.zshenv` previously caused `uv run` and `ruff` ENOENT failures in unattended jobs (`movers` lesson 38). Floating `"latest"` tool specifiers also risk silent supply-chain drift.

## Decision Outcome

1. **Declarative Lockfile Spine (`jdx/mise` `2026.11.6` + `astral-sh/uv` `0.13.7`):** Pin exact versions of all 20 CLI binaries in `mise.toml` with `[settings] lockfile = true` (`mise.lock`: 174 platform/checksum targets) and mirror the core SOTA CLI pins in user-global `~/.config/mise/config.toml` so every repository on this Mac inherits a consistent baseline.
2. **Universal Non-Interactive `PATH` (`~/.zshenv`):** Export `$HOME/.local/share/mise/shims` and `$HOME/.local/bin` in `~/.zshenv` so every Orca automation, MCP server, Git hook, and subagent resolves `uv`, `ruff`, `ty`, `rg`, `fd`, `ast-grep`, `duckdb`, `gitleaks`, `omc`, `omx`, `srt`, `bd`, `codegraph`, and `codebase-memory-mcp` without interactive shell activation.
3. **Locked Python Quant Environment (`pyproject.toml` + `uv.lock`):** Lock all 58 Python packages (`polars==2.1.0`, `duckdb==2.0.0`, `pandera==0.35.0`, `exchange-calendars==4.13.2`, `ml4t-diagnostic==0.2.0`, `skfolio==1.12.7`, `statsmodels==0.15.0`, `hypothesis==6.170.15`, `pytest==9.2.0`) on CPython `3.14.10`.

## Alternatives Considered

- **Homebrew `Brewfile`:** Not installed on this Mac; `Brewfile` is a rolling inventory rather than a cryptographic version lock.
- **Nix / nix-darwin:** High operational overhead for a single-owner macOS trading workstation compared to `mise.lock` + `uv.lock`.

## Verification Witness

- `env -i HOME="$HOME" zsh -c 'command -v uv omc rg ast-grep gitleaks'` resolves all shims in a clean non-interactive shell.
- `mise exec -- uv sync --locked` resolves 58 packages offline in `<300ms`.
