# ADR-0033: v3.9.7 Pre-Registered Trial `#95` (`H095`) Two-Stage Lit-Queue to `<= 10.0 bps` Marketable Collar Module & `15s` Sweep-Toxicity Law

- **Status:** Accepted
- **Date:** 2026-11-18
- **Layer:** L2 / L3 / L8 / L12 / L13 (`P0–P5` × `T1–T5` × `H0–H7`)
- **Evidence Grade:** E4 (`33` ADRs, `61/61` Pytest & Hypothesis Property Tests, Pre-Registered Trial `#95` `spec_sha256 = 5abe51a4caac...` Across `700` `XNYS` Sessions `<= 2026-10-15`)
- **GitHub Evidence:** https://github.com/native-agent-stack/sota-harness-foundation, https://github.com/native-agent-stack/meridian, https://github.com/nkaz001/hftbacktest, https://github.com/ml4t/diagnostic
- **Revisit Trigger:** Pre-registered Trial `#96` (`t*(96) = 4.1882`) dry-powder `15s` bid-survival collar study or `2026-12-06` `23/5` Consolidated SIP cutover

## Context and Problem Statement

Trial `#94` (`H094`, `meridian 0061`) proved that tightening `H091` to `entry_spread_bps <= 10.0`, `ADV_20d >= $20M`, and `OFI >= 0.25` lifted lit round-lot net return by `+25.886 bps` (`-23.732 -> +2.154 bps`), while leaving `107 / 319` (`33.54%`) immediate runaway breakouts unfilled (`-97.274 bps` pure-passive adverse selection). Pre-registered Trial `#95` (`H095_TWO_STAGE_LIT_QUEUE_15S_TO_10BPS_MARKETABLE_COLLAR_ORB_CPCV`, `spec_sha256 = 5abe51a4caacf4bf6955a331b495310fae1791a8d74a76c111bc9e6a35b5f4fa`, `t*(95) = 4.1858`) tested a `[0..15s]` strict lit round-lot passive bid escalating at `+15s` to a `<= +10.0 bps` marketable ask collar (`ap_15s <= ap_entry * 1.0010`, `spread_15s_bps <= 10.0`, `as_15s * 100 >= order_qty`).

## Decision Outcome

1. **Ship `src/cc_sota_harness/h095_two_stage_hybrid_collar_prewall.py` & `tests/test_h095_two_stage_collar.py`:**
   - Implement `is_lit_roundlot_queue_trade()` and `simulate_h095_two_stage_hybrid_orb_fill()`, property-tested via Hypothesis to guarantee Stage-2 collar fills never chase beyond `+10.0 bps` ask drift, never fill when live spread `> 10.0 bps` or round-lot ask depth `< order_qty`, and hard-block `entry_hhmm_et >= "1550"`.
2. **Codify the `H095` Stage-1 vs Stage-2 Empirical Bifurcation (`PROTECTIVE_FILTER_OR_GOVERNANCE`, `v3.9.7`):**
   - Across all `319` shielded signals (`189` fills / `157` dates), `H095` improved adverse selection by `+47.804 bps` (`-97.274 -> -49.470 bps`) and `C(6,2)` disjoint CPCV positive splits from `7/15` to `8/15` (median `+0.0219`), while honestly failing `ALPHA_STRATEGY_MINOR` (`-1.740 bps` net `1x`, `t = -0.1089 < 4.1858`, advancing `N = 95 -> t*(96) = 4.1882`).
   - Decomposition exposed a `+24.041 bps` bifurcation: Stage-1 `[0..15s]` immediate passive fills (`n = 134`, `80/134 = 59.7%` `trade_through`) suffered `-8.736 bps` net `1x` (`-14.108 bps` `2x`) seller-sweep toxicity, whereas Stage-2 `+15s` bid-survived `<= 10.0 bps` collar fills (`n = 55`) earned `+20.779 bps` gross / `+15.305 bps` net `1x` / `+9.832 bps` net `2x`.

## Alternatives Considered

- **Promoting `H095` on `ALPHA_STRATEGY_MINOR` by isolating only the `n = 55` Stage-2 subset post-hoc:** Rejected; post-hoc subset selection violates pre-registration integrity (`Mandatory 7-Gate Research Loop`). Dry-powder `15s` bid-survival confirmation must be pre-registered independently as Trial `#96` (`t*(96) = 4.1882`).

## Verification Witness

- `uv run python scripts/architecture_catalog.py` & `--check` (`33 ADRs valid, 0 drift`), `uv run ruff check .`, `uv run pytest -q` (`61 passed`), and `gitleaks git --staged --no-banner` (`0` leaks).
