# ADR-0030: Master Harness, 7-Feed PIT DataFeed, 6-Pillar Trading Ranking & Dual-Machine Execution Architecture (`v3.8.0`)

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L0–L12 × P0–P5 × T0–T8 × H0–H7 × T1–T5 (Full-Ecosystem Architectural Synthesis)
- **Evidence Grade:** E4
- **Revisit Trigger:** `2026-12-06` `23/5` Consolidated SIP cutover, `PostWallCohortLedger` reaching `N >= 250`, or upstream pin rotation in `PINS.md`

## Context and Problem Statement

Across `ADR-0001..0029`, the `native-agent-stack` open-core harness and trading fleet evolved modular contracts for multi-runtime orchestration, workstation placement, pre-wall statistical gates, and broker rate-limiting. Finalizing `v3.8.0` required one authoritative Master Architecture ADR binding:
1. How SOTA research skills (`microstructure-and-sec-catalyst-lab`, `stockbee-episodic-pivot-analyzer`, `stockbee-momentum-burst-screener`, `sota-quant-research-protocol`, `sota-dimensional-and-property-invariants`) connect the **7 canonical Point-in-Time (`PIT`) DataFeeds** (`sota-research-feeds.v2`) into the **6-pillar / 3-composite Trading Ranking System** (`sota-ranking-and-datafeeds.v2`);
2. How the **Multi-Model Harness Plane** (`H0–H7`, `cc-lead` `claude-fable-5-2` `xhigh` + `OMC` Runtime v2, `17` CLI runtimes, `8` orchestration frameworks, symmetric `:6770` `Mac M5 Max <-> Noesis` + `Noesis-Carbon` `ext4` Orca mesh) governs the **5-Stage Trading Plane** (`T1–T5`: `Sim -> Pre-Wall <= 2026-10-15 -> Paper :8787/:8799/:4002 -> Empirical-Bayes -> Vault`).

## Decision Outcome

1. **7-Feed PIT DataFeed Spine (`sota-research-feeds.v2` -> `sota-ranking-and-datafeeds.v2`):**
   - Every ranking pulse and pre-wall replay ingests strictly PIT-aligned observations across (1) `alpaca_sip` (`bs * 100.0` CTA/UTP round lots, `'F'` lit ISO vs `'I'` odd-lot, `BJZZ 2021` institutional round/midpoint vs sub-penny retail `x == 'D'`, `Lee-Ready 1991` signed dollar `OFI`), (2) `alpaca_boats` (`20:00–04:00 ET`, `<= 900s` quote expiry, `2026-12-06` `23/5` flag), (3) `alpaca_raw_vs_all_adjustment` (`RAW` liquidity/spread/ticks vs `ALL` split-adjusted returns & `RVOL_tod`), (4) `sec_edgar_acceptance_datetime` (`<= 0.067 req/s` Atom `getcurrent`, `15m` Vega/Tetlock half-life, `S-3`/`424B*`/`EFFECT` dilution block), (5) `finra_regsho_cnmsshvol_t1` (`T-1` short-vol + Rule 4560 `T+8` NYSE bd short-interest), (6) `corporate_actions_split_guard` (`XNYS` completed-session `bar_age_sessions == 0` gate), and (7) `ibkr_paper_4002_l1` (`2,700/300 msg/min` reserve).
2. **6-Pillar Session-Regime Ranking + `H090` Execution-Quality Tiers:**
   - Rank candidates across `move`, `unusual_vol` (`QuantConnect/Lean` `RVOL_tod` 20-session same-clock-bucket median), `inst_dark`, `iso_urgency`, `overnight`, and `catalyst` (`[0..100]`), separating true `>= 8h`-silent `TAPE_PRE_NEWS_IGNITION` (`Gervais-Kaniel-Mingelgrin 2001`) from `1,800s..28,800s` intraday post-news drift, and routing orders by `H090`/`H089` microstructure tiers (`TIER1` `<= 10 bps` spread + `>= 25%` `OFI` passive bid: `+20.84 bps` 1x, `5/5` `CPCV`; `TIER2` `<= 35 bps` two-stage hybrid queue + post-Gain-Lock `50/50` Core+Runner convexity; `TIER3` blocked) on normalized `[0..100] * ucb_priority_weight` scores.
3. **Sovereign Harness × Trading Separation (`singleActiveBrokerHostOnly = true`):**
   - `cc-lead` (`oneModelPerConversation = true`) orchestrates isolated child worktrees and offloads `56`-thread `CPCV` / `29,500`-file pre-wall sweeps onto `Noesis` / `Noesis-Carbon` (`ext4`) whenever `Mac M5 Max` holds active RTH Paper broker lanes (`:8787`, `:8799`, `:4002` under `ADR-0022 <= 2.00%` stops; live real-money execution 100% hard-refused).

## Alternatives Considered

1. **Score ranking candidates on full-day average volume or `filingDate` instead of `RVOL_tod` and `acceptanceDateTime`:** Rejected — introduces U-shaped open/close volume bias and after-hours `16:05` ET lookahead leakage.
2. **Allow `1h–8h` old intraday headlines to trigger `TAPE_PRE_NEWS_IGNITION`:** Rejected — violates Vega (2006) / Tetlock (2007) public-information arrival decay (`sota-compounding-lab` `ADR-0010`).

## Verification Witness

- `uv run python scripts/architecture_catalog.py --check` (`30 ADRs valid, 0 drift`), `uv run ruff check .`, `uvx ty@0.0.104 check src scripts tests`, `uv run pytest -q`, and `gitleaks detect --no-git --no-banner` (`0` leaks).
