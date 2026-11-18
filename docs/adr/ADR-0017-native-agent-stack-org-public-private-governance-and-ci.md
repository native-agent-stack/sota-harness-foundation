# ADR-0017: `native-agent-stack` GitHub Organization Public/Private Split, Isolated Worktrees & SHA-Pinned CI

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** L0 / L1 / L3 / L8 / L9 (`T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Addition of a new repository tier in `https://github.com/native-agent-stack` or GitHub Actions billing/runner policy change

## Context and Problem Statement

Our multi-model harness and quantitative trading ecosystem spans Claude Code Lead (`cc-lead`, `claude-fable-5-2` `xhigh`), Antigravity (`gemini-4-carbon-high`), Codex (`gpt-6.2-astra` `max`), OpenCode/OMO, Pi/OMP, DeepSeek Harness (`dsh`), simulation (`meridian`), live 24/5 paper execution (`sota-mover-ranker`, `sota-dynamic-trail-c`, `astrolabe`), and shared cross-session memory (`sota-bus`). Consolidating these repositories inside one GitHub Organization (`https://github.com/native-agent-stack`) must simultaneously achieve two competing goals:
1. **Unlimited Free GitHub Actions CI:** Public repositories on GitHub receive unlimited free Ubuntu and macOS Actions minutes for continuous linting, MADR 4.0 catalog verification, Hypothesis property testing, and `RuleBasedStateMachine` stateful fuzzing.
2. **Strict Alpha, Lake-Trial & Privacy Isolation:** Proprietary pre-wall empirical lake studies (`H05` tick/quote trial reports), live strategy weights, sibling audit trails, and broker execution runtimes must remain strictly `PRIVATE` with zero involuntary private-Actions minute burn, zero secrets, and zero hardcoded macOS user home paths (`<home>/<user>/`) in tracked files.

## Decision Outcome

We organize the entire multi-model and trading ecosystem inside **`https://github.com/native-agent-stack`** under a two-tier Public/Private split coordinated via `sota-bus` work leases and isolated Orca git worktrees:

1. **Public Open-Core & Unlimited-CI Tier (`PUBLIC`, automated `push` + `pull_request` SHA-pinned Actions):**
   - `native-agent-stack/.github` (`4fe823289ed3eae6ecf2c3fa38217002f5ea4f6f`): Org profile, reusable SHA-pinned CI workflows, and master `ECOSYSTEM_ORG_MANIFEST.json`.
   - `native-agent-stack/sota-harness-foundation` (published from this harness's open-core foundation): Multi-model routing matrix (`config/multi-model-routing.json`), MADR 4.0 catalog validator (`architecture_catalog.py`), 5-stage `Sim -> Backtest -> Paper -> Compounding` engine (`compounding_pipeline.py`), pinned `Nautilus`/`hftbacktest` parity (`upstream_execution_parity.py`), and institutional frontier gates (`gates.py`, `institutional_frontier.py`) running on `ubuntu-latest` + `macos-latest`.
   - `native-agent-stack/sota-multi-model-workflows` (`ad35acf26efbbcf33ce03f99f083cc8ee166a562`): 9 LLM-native multi-model workflows + SQLite WAL peer-bus kit.
   - `native-agent-stack/sota-upstream-shelf-lock` (`045ddbc676a540906b3e3578d2778824e49a6ab6`): 18-repo trading upstream 40-char SHA lock verifier.
   - `native-agent-stack/agy-sota-harness` (`17b1710348643fa19f43ef6f045d7c0b7598044c`), `native-agent-stack/dsh-sota-harness` (`980d47a7703e0a1f250ef6787bea0da2d88abfe6`), `native-agent-stack/astrolabe` (`f3511522c048ecde5f1a538387d9cf5b77f81262`), and `native-agent-stack/native-agent-stack` (`4b8ca6208e8b2bb656f662df2708f6a70a3c7830`).
2. **Private Proprietary Research, Vault & Paper Execution Tier (`PRIVATE`, `0` involuntary Actions burn):**
   - `native-agent-stack/cc-sota-harness`: Full 27-runtime `cc-lead` harness retaining pre-wall `H05` empirical lake findings, adversarial sibling audits, Claude/MCP/SRT configs, and `workflow_dispatch` SHA-pinned validation.
   - `native-agent-stack/sota-mover-ranker` (`bae497602334cf8967c2af3491b55f6727fe601f`), `native-agent-stack/sota-dynamic-trail-c` (`d6e25bf82fb8963c8629f648bafbf84222441f6b`), `native-agent-stack/trading-sota` (`c7d60f5b9897ccb30223481de894ce9746e20505`), `native-agent-stack/meridian` (`4dd0c20ef3c87159e783aea8d774759358bf1413`), `native-agent-stack/sota-private-vault`, `native-agent-stack/sota-strategy-vault`, and `native-agent-stack/ecosystem-records`.
3. **Zero Home-Path & Supply-Chain Action Pinning:**
   - Replace hardcoded home paths in `.mcp.json`, `.claude/settings.json`, and `policies/srt-trading-worker.json` with `scripts/mcp_stdio_launcher.py` (`pathlib.Path.home()`) and `~` globs, enforced by `doctor.py` and `test_sota_ecosystem.py`.
   - Pin GitHub Actions by immutable 40-char commit SHA (`actions/checkout@11d5960a326750d5838078e36cf38b85af677262`, `astral-sh/setup-uv@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86`) with `permissions: contents: read`.

## Alternatives Considered

1. **Make all repositories `PRIVATE` and run `on: push` GitHub Actions everywhere:** Rejected because private repositories consume a finite monthly Actions quota (`2,000` free minutes), whereas splitting open-core mathematical/harness infrastructure into `PUBLIC` repositories unlocks unlimited free Ubuntu + macOS CI while keeping proprietary alpha 100% private.
2. **Make `cc-sota-harness` itself `PUBLIC`:** Rejected because `docs/reports/H05_PREWALL_MICROSTRUCTURE_STUDY.md` and `CODEX_ASTRA_ADVERSARIAL_AUDIT.md` contain proprietary empirical Parquet-lake trial diagnostics and internal sibling-repo audit details.

## Verification Witness

- `scripts/doctor.py` enforces `0` tracked macOS user home-path occurrences across `git ls-files`, `actionlint` clean on `.github/workflows/validate.yml`, and `18 ADRs valid, 0 drift`.
- `gh run list -R native-agent-stack/sota-harness-foundation` verifies live cloud CI (`ubuntu-latest` + `macos-latest`) completing `success`, while `gh api repos/native-agent-stack/cc-sota-harness --jq .private` verifies `true`.
