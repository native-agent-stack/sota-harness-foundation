# ADR-0019: Complete Legacy Repository Harvest, Supersession Seal & Clean Environment Convergence

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** L0–L11 (`T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Never for sealed archives; revisit only if a new external repository is folded into `https://github.com/native-agent-stack`

## Context and Problem Statement

Across September–November 2026, iterative prototypes (`Qingjian`, `Vela`, `Eddyline`, `Northstar`, `Horizon`, `Strata`, `Peregrine`, `Sextant`, `Canon`, `Edge`, and `Movers`) accumulated 47 historical repositories across personal, `deer-opus`, and local workspaces. Leaving legacy repositories unarchived, unharvested, or duplicated in Orca scratch paths creates three concrete hazards:
1. **Lost Empirical Post-Mortems:** Hard-won empirical findings in `edge/LEARNED.md` (`Canon`'s 122-entry chasing loss, 1m OHLC ambiguity, ex-ante MDE sizing, 4-minute disconnect naked shares) and `movers` (`src/movers/auctions.py` `'6'`-before-`'M'` closing cross fixing 887 Arca small-lot mispricings, plus one-writer-per-symbol isolation) risk being forgotten unless encoded as executable gates.
2. **Boundary & Visibility Drift:** Stale public prototype mirrors (`sextant*`) or duplicate Orca scratch clones risk split-brain edits and private Actions minute burn.
3. **Lack of Auditable Lineage:** Every superseded repository must map via immutable 40-character Git commit SHA to its canonical active owner inside `https://github.com/native-agent-stack`.

## Decision Outcome

We execute a complete, non-destructive **Harvest -> Codify -> Seal -> Clean** convergence across every layer:

1. **Code-Enforced Harvest of Legacy Invariants (`institutional_frontier.py` & `compounding_pipeline.py`):**
   - **Auction Cross Priority (`select_listing_exchange_auction_print`):** Harvested from `movers/src/movers/auctions.py` — enforces `('O', 'Q')` for opening and `('6', 'M')` for closing sorted by `(-size, venue, event_ts_ns)`, eliminating the 887-symbol Arca small-lot `'M'` distortion.
   - **One-Writer-Per-Symbol Isolation (`check_one_writer_symbol_isolation`):** Harvested from `movers/DECISIONS.md` — hard-refuses (`PermissionError`) blind whole-symbol `close_position` calls and cross-lane symbol collisions.
   - **Ex-Ante HLZ Minimum Detectable Effect (`compute_ex_ante_mde_bps`):** Harvested from `edge/CLAUDE.md` & `edge/LEARNED.md` — computes $\text{MDE}_{\text{bps}} = t^*(N) \cdot \sigma_{\text{fit}} / \sqrt{D_{\text{OOS}}}$ prior to reading held-out data; recorded as E4 lessons `c822b9c487fbac73` and `3a05dbf2dfd2cba7` in `~/.agents/wiki/LESSONS.md`.
2. **47-Repository Immutable Lineage & Supersession Ledger (`config/legacy-harvest-manifest.json`):**
   - Seals local `edge` -> `PRIVATE` archived `native-agent-stack/legacy-edge-202611` (`064366249313349b82235a92eadd51d21a09f70e`, `Actions=disabled`) and local `movers` -> `PRIVATE` archived `native-agent-stack/legacy-movers-202611` (`b9ada794259277193f0fbeca33e63890e230ad9f`, `Actions=disabled`), alongside `legacy-agent-stack-202610` (`4b8ca6208e8b2bb656f662df2708f6a70a3c7830`), `ecosystem-records` (`265a4d9f6c9d678c2d59fe8d437b9a4ea00581c5`), `deer-opus/meridian` (`9e412748b5dcbeffeb8014da9802e6a30c74f70e`), and all 42 superseded personal trading/harness prototypes (locked `PRIVATE` + `archived=true`, while keeping 8 unrelated personal sound/course/NAS/fork repositories untouched).
3. **Zero Private Quota Burn & Clean Orca/Workstation State:**
   - Disables GitHub Actions across 100% of `PRIVATE` repositories in `native-agent-stack` (`0` private quota burn), reserving automated `push`/`pull_request` CI exclusively for `PUBLIC` open-core repositories (`sota-harness-foundation`, `agy-sota-harness`, `dsh-sota-harness`, `sota-compounding-lab`, `sota-multi-model-workflows`, `sota-upstream-shelf-lock`, `astrolabe`, `native-agent-stack`, `.github`).
   - Prunes duplicate `.gemini/antigravity/scratch/*` clones and repoints active local `origin` remotes to `https://github.com/native-agent-stack/*.git`.

## Alternatives Considered

1. **Permanently delete legacy GitHub repositories:** Rejected because non-destructive `PRIVATE` + `archived=true` sealing preserves 100% cryptographic commit provenance at zero Actions or maintenance cost.
2. **Archive historical lessons as prose only without executable validators:** Rejected per `<user_rules>` ("Empirical Done" — prose without deterministic tests decays).

## Verification Witness

- `validate_legacy_harvest_manifest()` in `scripts/doctor.py` and GitHub Actions verifies all 47 archived repository records, 40-char commit SHAs, `archivedReadOnly=true` flags, and `native-agent-stack/*` successor mappings (`0` errors).
- `pytest -v` verifies Hypothesis properties for `compute_ex_ante_mde_bps`, `select_listing_exchange_auction_print` (`'6'` vs Arca `'M'`), and `check_one_writer_symbol_isolation` (`PermissionError` on cross-lane/blind-close).
