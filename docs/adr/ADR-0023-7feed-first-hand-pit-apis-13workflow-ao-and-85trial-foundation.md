# ADR-0023: 7-Feed First-Hand PIT APIs, 13-Workflow v3.3.0 AO Automation & 85-Trial Empirical Execution Foundation

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L2 / L3 / L6 / L8 / L11 (`T0–T8`)
- **Evidence Grade:** E4
- **Revisit Trigger:** Trial `N >= 86` HLZ clearance (`t >= 4.1631`), `2026-12-06` `23/5` SIP cutover, or `PostWallCohortLedger` reaching `N >= 250` live Paper fills

## Context and Problem Statement

Building on `ADR-0022` (`Canon 0169..0176` upstream contracts and bidirectional `sota-workstation coop`), the foundation harness required execution-verified Turn-0 workflow automation, live first-hand catalyst DataFeed APIs, and updated empirical trial governance (`N = 85`, `t*(86) = 4.1631`) so multi-model agents (`Antigravity`, `Claude Code`, `Codex`, `DSH`, `Orca`) never promote underpowered slices, stale media rehashes, or unscaled passive queue assumptions.

## Decision Outcome

We bind the foundation harness (`config/strategy-compounding-manifest.json` `v1.1.0`) to the newly landed research automation, 7-feed PIT execution surface, and `85`-trial empirical ledger across `sota-upstream-shelf-lock` (`v2.0.0` `@ 075e66b542`), `sota-multi-model-workflows` (`v3.3.0` `@ 50aad143db`), `agy-sota-harness` (`@ ceb78426be`), `sota-compounding-lab` (`@ d791f8adb4`), `astrolabe` (`@ 6016e0798b`), `sota-mover-ranker` (`@ 3639663a78`), `sota-dynamic-trail-c` (`v0.8.0` `@ 4b87d23e78`), `sota-private-vault` (`@ 527cee56fe`), and `native-agent-stack` (`@ dac24e5293`):

1. **7-Feed `sota-research-feeds.v2` First-Hand Early-Reaction PIT Contract & `16`-Tool `:8787` MCP Surface:**
   - Standardize Turn-0 `_sota_kit.py` `v3.3.0` bootstrap and MCP tools (`sota_get_research_feeds`, `sota_get_first_hand_incentives`, `sota_get_converged_strategy_templates`) across `alpaca_sip` (`04:00–20:00` ET), `alpaca_boats` (`20:00–04:00` ET + `2026-12-06` `23/5` SIP cutover auto-probe), `alpaca_raw_vs_all_adjustment`, `sec_edgar_acceptance_datetime` (`<= 0.067 req/s` live Atom poller, `15m` exponential freshness half-life decay, `424B*`/`S-3` dilution block below `USD 2B` float), `finra_regsho_cnmsshvol_t1`, `corporate_actions_split_guard`, and `ibkr_paper_4002_l1` (Rule 612 `25..75 bps` `StopLimitOrder` collars).
   - Enforce `<50ms` `EXEC_WAKE_EVENT` wakeup, `MAX_SPREAD_BPS = 35.0`, `math.isfinite()` positive-inclusion `<= 2.00%` initial stops (Meridian `ADR-0022`), and 4 canonical strategy templates (`PRE_TRAVEL_EARLY_IGNITION`, `FIRST_HAND_SEC_EPISODIC_PIVOT`, `MEGA_CAP_NEAR_LOSSLESS_ORB`, `CLIMAX_VWAP_MEAN_REVERSION`).
2. **13-Workflow `v3.3.0` Multi-Model `AO` & End-to-End Research-Convergence Suite:**
   - Land Workflow `#12` (`ao_multi_model_convergence_workflow.py`, `8`-slot `ComposioHQ/agent-orchestrator` lifecycle with frozen-assertion test protection and telemetry-derived `meshState` offline failover) and Workflow `#13` (`research_convergence_landing_workflow.py`, 4-phase `ADR-0004` 64-hex `seed_input_sha256` + `18` 40-hex upstream pin + 7-feed PIT validator, `__file__ in globals()` `<workflow>` namespace guard).
3. **85-Trial Empirical HLZ Proofs & Next-Queue Hurdle (`t*(86) = 4.1631`):**
   - Record `Trial #84` (`sota-dynamic-trail-c` `v0.8.0`: `+19.73 bps/trade` OOS lift, `-84.4%` `CVaR_95` reduction vs static `200 bps` stops, and `PostWallCohortLedger` toward `N >= 250`) and `Trial #85` (`H085` across `14,750` nanosecond SIP files, `577` dates `<= 2026-10-15`: `hftbacktest::RiskAdverseQueueModel` with `bs * 100.0` CTA/UTP round-lot scaling filled `86.41%` `1,393 / 1,612` at `10:30` ET bid, flipping net `1x` to `+7.908 bps` and `2x` to `+2.374 bps` for a `+13.55 bps` passive-vs-taker lift while honestly logging `FAILED` at `t = 0.8151 < 4.1604`).

## Alternatives Considered

1. **Permit unscaled round-lot L1 passive fills (`bs` without `* 100.0`) or midpoint execution:** Rejected — understates L1 queue depth by `100x` and hides `-4.384 bps` Glosten–Milgrom adverse selection on filled limits vs `+37.72 bps` unfilled runaways.
2. **Rely on secondary news headlines without `acceptanceDateTime` `15m` half-life decay:** Rejected — introduces multi-minute rehash lag and misses first-hand `8-K` catalyst ignitions.

## Verification Witness

- `ao_multi_model_convergence_workflow.py` (`qualification_receipt_sha256=32925b6f5ba358904ac70af6f8e881c70b930403089c5bcff665227afc040cb2`): surfaced and remediated `CANONICAL_MODEL_VENDORS` Stage-3 allowlist, `DataFeedPITContract` (`FINRA Rule 4560` `T+8` short-interest & `T-1` short-volume lag), `IBKR_PROTECTIVE_EXIT_RESERVE_MPM = 300` (`2700`/`3000` split) + `127.0.0.1` loopback guard, and `.gitleaks.toml` `--no-git` cache hygiene (`test_ao_remediation_vendor_allowlist_pit_contract_and_ibkr_reserve` `PASS`).
- `shelf_lock.research_workflow` (`N=85`, `577` dates, `sigma=145 bps`): `approved_to_preregister=True`, `hlz_t_hurdle=4.1604`, `min_trl_days_at_target_sr=486.0`; `45`-date underpowered slice rejected (`sr_min_ann=9.8453 > 5.00`); `simulate_risk_adverse_buy_queue` verified `queue_depleted` fill (`PASS`).
- `research_convergence_landing_workflow.py` (`H08_FIRST_HAND_CATALYST_IGNITION`, `seed_input_sha256=aa47f11693c0177840681809404737166ab5adaacf2c20e8f9aeeb3bcd620fd9`): `convergence_claim_valid=True`, `feed_count=7`, `upstream_pin_count=18`, `sota_doctor=11/11 PASS`.
- `scripts/architecture_catalog.py --check`, `validate_compounding_manifest()`, `ruff`, `ty`, `gitleaks detect --no-git`, and `pytest` (`PASS`, `23 ADRs valid, 0 drift`).
