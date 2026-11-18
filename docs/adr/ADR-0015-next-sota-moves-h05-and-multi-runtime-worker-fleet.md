# ADR-0015: Next SOTA Moves (`H05` Tick Microstructure Trial #79) & Multi-Runtime Orca Worker Fleet

- **Status:** Accepted
- **Date:** 2026-11-17
- **Layer:** L1 / L3 / L4 / L11 (`T1–T6`)
- **Evidence Grade:** E3
- **Revisit Trigger:** Completion of `H05` Trial #79 outcome logging on `sota-peer-bus` or `2026-12-06` 23/5 SIP session cutover

## Context and Problem Statement

With `H04` (1.28B 1-minute OHLCV bars, Trial #78) honestly rejected at $t = 0.8503 < 4.1408$ due to bar-level aggregation masking sub-minute aggressive buy flow and dark-pool midpoint accumulation, and with `v0.4.0` (`9816ed8`) merged in `sota-mover-ranker` and `sota-dynamic-trail-c`, the ecosystem's highest-leverage next moves require parallel execution across distinct frontier model families without dirtying `cc-lead`'s `main` checkout or touching read-only sibling repositories.

## Decision Outcome

We execute the **Four Next SOTA Moves** through **5 clean, role-specialized multi-model Orca workspaces** anchored on `cc-sota-harness`:

1. **Move #1 — Pre-Registered `H05` Pre-Wall Tick/Quote Microstructure Study (`Trial #79`, HLZ $t^* \ge 4.1437$, `<= 2026-10-15`):**
   - Immutably pre-registered on `sota-peer-bus` (`H05_PREWALL_TICK_MICROSTRUCTURE_IGNITION_DYNAMIC_TRAIL`, `spec_sha256: f9e921cb4d3f62ed62bccb824c88895ca72b7591a1647a1349a2aad70619d9c1`).
   - Implemented in `src/cc_sota_harness/microstructure_h05.py` combining Boehmer-Jones-Zhang-Zhang (`BJZZ`, *JoF* 2021) off-exchange (`x == 'D'`) NBBO midpoint dark-pool prints (`0.40..0.60` sub-penny cents), ISO buy toxicity (`>= 55%`), `vol_z >= 2.3`, `rvol_tod >= 2.2`, FINRA RegSHO (`>= 50%`), SEC `S-3`/`424B5` zero-dilution shield, and conservative intrabar `bid`/`ask` quote-sweep dynamic trailing stops (`4–45 bps`, `ADR-0022 <= 200 bps` cap, `1x`/`2x` cost stress).
   - Dispatched to **`h05-prewall-lake`** (`Antigravity` `agy` `1.5.3` on `gemini-4-carbon-high`) to evaluate the read-only 37 GB `~/Documents/market-data` Parquet lake (`<= 2026-10-15`) and log the honest `CPCV` + `DSR` + date-clustered $t$-stat outcome.
2. **Move #2 — Cross-Family Adversarial Statistical & `20:00 ET` Cutover Audit:**
   - Dispatched to **`codex-astra-audit`** (`OpenAI Codex` `0.169.0` + `OMX` `0.22.10` on `gpt-6.2-astra` `max` effort) to red-team `gates.py`, `microstructure_h05.py`, and read-only `sota-mover-ranker` (`main @ 9816ed8`) for dimensional/IEEE-754 edge cases, XNYS half-day/holiday boundaries, and `20:00 ET` `SIP -> BOATS` feed-cutover races.
3. **Move #3 — Upstream `Nautilus` + `hftbacktest` Queue-Position Fill Parity:**
   - Dispatched to **`omo-opencode-exec`** (`OpenCode` `2.3.0` + `oh-my-openagent` `5.1.75` `OMO`) to synthesize exact `~/Documents/upstream/nautilus_trader` (`SpreadAnalyzer`, `ExitGate`) and `~/Documents/upstream/hftbacktest` queue-position fill rules into a unit-tested execution-parity specification.
4. **Move #4 — Cross-Harness Manifest & `Pi` / `OMP` Ecosystem Verification + `CC Lead` Synthesis:**
   - Dispatched to **`omp-shelf-parity`** (`oh-my-pi` `omp` `18.22.0` / `pi` `1.5.2`) to audit cross-harness parity (`cc-sota-harness`, `agy-sota-harness`, `dsh-sota-harness`, `sota-doctor` `9/9`), with **`cc-lead`** (`claude` `2.1.326` on `claude-fable-5-2` `xhigh`) chairing the multi-model convergence on `main`.

## Alternatives Considered

1. **Run all four moves sequentially inside a single `cc-lead` session:** Rejected because 37 GB Parquet lake scans, 18-repo upstream shelf synthesis, and adversarial code red-teaming pollute a single context window and forfeit genuine cross-vendor model independence (`Claude Fable 5.2` vs `GPT-6.2 Astra` vs `Gemini 4 Carbon` vs `OMO`/`OMP`).
2. **Evaluate `H05` on post-wall (`>= 2026-10-16`) sessions or without SHA-256 pre-registration:** Rejected — violates the `<= 2026-10-15` study wall and inflates false-discovery risk under $N = 79$ cumulative trials ($t^* = 4.1437$).

## Verification Witness

- `sota-bus preregister` receipt: `trial_n=79`, `spec_sha256=f9e921cb4d3f62ed62bccb824c88895ca72b7591a1647a1349a2aad70619d9c1`.
- `pytest -v` verifies `BJZZ` sub-penny classification, `H05` post-wall leakage rejection, Hypothesis quote-sweep `2x <= 1x <= gross` cost monotonicity, and `15 ADRs valid, 0 drift`.
