# ADR-0024: Trial #88 (`H088`) Passive-Bid × Range-Scaled Trail Phase Diagram, Skewness-Truncation Proof & 424-Star SOTA Reference Lock

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L2 / L3 / L6 / L8 / L11 (`T1–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Pre-registered Trial `N >= 89` (`t*(89) >= 4.1709`), `PostWallCohortLedger` reaching `N >= 250` real Paper round-trips, or `2026-12-06` `23/5` SIP cutover

## Context and Problem Statement

Across Trials `#80` (`H06`), `#85` (`H085`), and `#87` (`H087`) on the strictly pre-wall (`<= 2026-10-15`) `14,750`-file nanosecond CTA/UTP SIP opening-range breakout (`published-orb`) + `bars-1min` + PIT SEC/FINRA lake:
1. `H06` (`Trial #80`, marketable ask-taker to `16:00` ET close, `1,611` events / `600` dates) lost `-5.641 bps` net `1x` (`t = -0.80`) solely from paying the `8.21 bps` entry half-spread.
2. `H085` (`Trial #85`, `1`-lot `hftbacktest::RiskAdverseQueueModel` passive `bp_entry` limit to `16:00` ET close, `1,393` fills / `577` dates) flipped **both** `1x` (`+7.908 bps`) and `2x` (`+2.374 bps`) net positive (`+13.55 bps` maker-vs-taker lift), leaving full-day hold dispersion (`SE = 9.70 bps`, `t = 0.8151 < 4.1604`) uncompressed.
3. `H087` (`Trial #87`, passive bid × `10 bps` uniform mega-cap scratch over `240s`, `2,765` fills / `676` dates) cut return standard deviation by `-87.5%` (`225.94 -> 28.21 bps`) and `CVaR_95` by `-88.2%`, but yielded `-5.70 bps` (`t = -10.66`) because a uniform `10 bps` scratch sits inside `35–80 bps` mid/small-cap ORB `1m` noise.

We therefore pre-registered and executed `Trial #88` (`H088_PASSIVE_BID_X_VARIANCE_COMPRESSING_DYNAMIC_TRAIL`, `spec_sha256 = a37a033826006afae796c325251df5a8628082875e43d78241fe0c60c25e43fc`, `t*(88) = 4.1683`) in `src/cc_sota_harness/passive_bid_trail_prewall.py` to test full-notional (`USD 25,000`) `RiskAdverseQueueModel` (`bs * 100.0` shares) passive bid entry paired with `1.2x` causal pre-entry `1m` range-scaled (`[45 bps, 180 bps <= ADR-0022]`) `ADVERSE_STOP_FIRST` trailing + `+60 bps` (`65%` MFE) Gain-Lock through `15:55` ET.

## Decision Outcome

We adopt `passive_bid_trail_prewall.py` as an open-core execution-physics & skewness-audit module, archive `H088` honestly as `REJECTED_PREWALL` in `config/strategy-compounding-manifest.json` (`v1.2.0`), and lock the resulting **4-Trial Microstructure Phase Diagram** and **SOTA Reference Canonicalization**:

1. **Empirical `H088` Findings (`2024-02-01 .. 2026-10-15`, `7,454` Liquid ORBs, `1,273` Shielded Fills Across `549` Dates):**
   - **Downside Tail & Variance Compression Confirmed:** Range-scaled (`mean = 84.837 bps`) `ADVERSE_STOP_FIRST` trailing reduced `CVaR_95` tail loss by **`-44.55%`** (`-724.614 -> -401.792 bps`) and date-clustered `SE` by **`-15.17%`** (`8.151 -> 6.915 bps`).
   - **Right-Tail Skewness Censoring & Full-Notional Adverse Selection Exposed (`Kaminski & Lo 2014` × `Glosten & Milgrom 1985`):**
     - Requiring full `USD 25,000` share depletion behind `bs * 100.0` resting depth (`86.83%` fill rate, `1,273 / 1,466`) incurred **`-46.372 bps`** unconditional adverse selection vs the `193` (`13.17%`) unfilled immediate breakout runaways.
     - Arming single-tranche `+60 bps` Gain-Lock (`65%` MFE retention) + `84.8 bps` `1m` trail exited **`97.8%` (`1,245 / 1,273`)** of positions before `15:55` ET (`291` quote trail, `800` bar trail, `154` initial stop, and only **`28`** reaching `15:55` ET), truncating the positively skewed afternoon ORB right tail and yielding `-15.160 bps` net `1x` (`-20.658 bps` `2x`, `t = -2.1925`, `DSR = 0.0`).
2. **Architectural Mandate for Next Pre-Wall Candidate (`Trial #89` `H089`) & Live Paper Guardians (`:8787` / `:8799`):**
   - **Never apply tight single-tranche Gain-Lock across `100%` of a positively skewed ORB mover.** Combine `50/50` Dual-Tranche Asymmetric Convexity (`Core` profit-lock + wide `Runner` Chandelier / `15:55` ET hold) with a **Two-Stage Hybrid Entry** (`50%` passive bid maker + `50%` stop-limit breakout join on the `13.2%` unfilled `+46.4 bps` runaways).
3. **Canonical SOTA Upstream & Academic Reference Lock (`424`-Star Matrix × `18` `40`-Char Pins):**
   - **Execution & Queue Physics:** `https://github.com/nkaz001/hftbacktest` (`5f3ec40b2afb764e0fea112f941ed85523ef4e88`, `queue.rs:42-96`), `https://github.com/nautechsystems/nautilus_trader` (`da6b57aefdd62b44f675e434ffcfefca7f4025dd`), `https://github.com/alpacahq/alpaca-py` (`c42add7c0a7026e2ead3ed64e76f4def2b99fda4`), `https://github.com/ib-api-reloaded/ib_async` (`ab629f34c1823ea4c1542f32f07377208a86bdfd`).
   - **Statistical Power, Multiplicity & PIT Data:** `https://github.com/ml4t/diagnostic` (`19e76072e64a18c9ba56130e4a7bcc0bc871f57e`, López de Prado, Lipton & Zoonekynd 2025 *ADIA Lab #19* `MinTRL`/`MDE` & `DSR`), `https://github.com/skfolio/skfolio` (`90e3fb907fab39d244d899f3caf4e9676889309c`, `CombinatorialPurgedCV`), `https://github.com/dgunning/edgartools` (`574c2bd15f6c629bceef03b6550ea8ac8abf3473`), `https://github.com/pola-rs/polars` (`7f902bd3ffd27ff82d14278a09a295ff2f7aed92`), `https://github.com/statsmodels/statsmodels` (`278ff9950636cdd4939b4055e339a8e681d79cab`), `https://github.com/QuantConnect/Lean` (`RelativeDailyVolume.cs`).
   - **Multi-Model Agentic Learning Harnesses (`424`-Starred & Beyond):** `https://github.com/stablyai/orca`, `https://github.com/Yeachan-Heo/oh-my-claudecode`, `https://github.com/Yeachan-Heo/oh-my-codex`, `https://github.com/obra/superpowers`, `https://github.com/EveryInc/compound-engineering-plugin`, `https://github.com/ComposioHQ/agent-orchestrator`, `https://github.com/trailofbits/skills`, `https://github.com/aannoo/hcom`.
   - **Primary Literature:** Harvey, Liu & Zhu (2016 *RFS*), Boehmer, Jones, Zhang & Zhang (2021 *JF*), Glosten & Milgrom (1985 *JFE*), Almgren & Chriss (2001 *JoR*), Kaminski & Lo (2014 *JPM*), Zarattini, Aziz & Barbon (2024/2025).

## Alternatives Considered

1. **Evaluate `1m` OHLC trailing stops with optimistic `high-before-low` intrabar ordering:** Rejected — inflates tight-stop expectancy by ratcheting `peak_px` before checking `low <= active_stop_px` (`INV-QUOTE-SWEEP-OVER-1M-OHLC`). `replay_adverse_stop_first_exit` enforces Phase-A nanosecond firm NBBO quote sweep followed by strictly pessimistic `ADVERSE_STOP_FIRST` (`low-before-high`) `1m` replay.
2. **Suppress or omit negative `Trial #88` from `HYPOTHESIS_LEDGER.md` and `strategy-compounding-manifest.json`:** Rejected — violates Harvey–Liu–Zhu family-wise multiplicity accounting (`N = 88 -> t*(89) = 4.1709`).

## Verification Witness

- `shelf_lock.research_workflow --trials-n 88 --dates 577 --sigma-bps 32.0`: `approved=True`, `hlz_t_hurdle=4.1683`, `min_trl_days_at_sr3=488.0`.
- `sota-bus preregister` & `outcome` (`Trial #88`, `spec_sha256=a37a033826006afae796c325251df5a8628082875e43d78241fe0c60c25e43fc`) + `E4` lesson `6a48731a67e9476a` persisted in `HYPOTHESIS_LEDGER.md` and `LESSONS.md`.
- `scripts/architecture_catalog.py --check`, `validate_compounding_manifest()`, `ruff check --no-cache`, `ty@0.0.104 check`, `gitleaks detect --no-git`, and `pytest -v` (including `Hypothesis` `@given` stop-bound and cost-monotonicity invariants): `24 ADRs valid, 0 drift, PASS`.
