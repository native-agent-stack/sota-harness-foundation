# UPSTREAM_EXECUTION_PARITY_SPEC — SOTA Move #3

- **Date:** 2026-11-17 · **Owner:** `omo-opencode-exec` (OpenCode 2.3.0 / OMO, `claude-sonnet-5-5` / `deepseek-v4.1-flash` tier)
- **Mandate:** ADR-0015 Move #3 (line 23-24); Upstream-First Charter `CLAUDE.md` rule 1.
- **Status:** E3 — all rules below transcribed from pinned source at verified commit, mirrored by an executable Python reference, and unit-tested.
- **Upstream boundary:** `~/Documents/upstream/` was read only. No file there was created, modified, or deleted.

## 1. Provenance (verified this session, not recalled)

| Upstream | Pin from `~/Documents/upstream/PINS.md` | `git rev-parse HEAD` | Clean tree | Source of truth |
|---|---|---|---|---|
| `nautilus_trader` | tag `v2.0.0rc9` | `da6b57aefdd62b44f675e434ffcfefca7f4025dd` | yes | `crates/indicators/src/ratio/spread_analyzer.rs`, `crates/model/src/{enums.rs,orders/builder.rs}` |
| `hftbacktest` | commit `5f3ec40b2afb764e0fea112f941ed85523ef4e88` (2025-12-23) | `5f3ec40b2afb764e0fea112f941ed85523ef4e88` | yes | `hftbacktest/src/backtest/models/queue.rs`, `hftbacktest/src/backtest/proc/{no,partial}partialfillexchange.rs`, `py-hftbacktest/src/lib.rs`, `docs/order_fill.rst` |

The executable mirror is `src/cc_sota_harness/upstream_execution_parity.py`; the tests are
`tests/test_upstream_execution_parity.py`. The pin-SHA guard test re-verifies these two
commits on every `pytest` run.

**Invariants preserved:** paper-only venues, ADR-0022 `<= 2.00%` protective stop, no position
without its exit, study wall `<= 2026-10-15` for any calibration (this spec runs no research),
and the read-only sibling-repository boundary. No keys, account IDs, or balances were read.

## 2. `nautilus_trader` — `SpreadAnalyzer` (exact pinned rules)

Source: `crates/indicators/src/ratio/spread_analyzer.rs` @ `da6b57ae`.

1. **State** (lines 36-44): `capacity`, `instrument_id`, `current = 0.0`, `average = 0.0`,
   `initialized = false`, `has_inputs = false`, `spreads: Vec<f64>`.
2. **Construction** (lines 115-143): zero capacity is accepted; `new_checked` calls
   `try_reserve_exact(capacity)` and rejects only an allocation overflow
   (`capacity > isize::MAX / size_of::<f64>()`). `new()` panics on that error via `.expect(FAILED)`.
3. **Instrument filter** (lines 70-73): a quote whose `instrument_id` differs is a no-op —
   it does not set `has_inputs` and does not touch the window.
4. **Initialization timing** (lines 75-82): on the first accepted quote `has_inputs = true`;
   `initialized` is set only when `spreads.len() == capacity` **at entry, before the push**.
   Therefore for `capacity = n > 0` the indicator becomes initialized on the **`(n+1)`-th**
   accepted quote; the pinned test at lines 200-218 feeds 9 of 10 quotes and asserts it is
   still uninitialized. For `capacity = 0` the first accepted quote initializes it.
5. **Per-quote calculation** (lines 84-102): `spread = ask - bid` in raw `f64` (no rounding,
   no tick conversion), `current = spread`, append, then if `len > capacity` evict index 0
   (FIFO). Recompute `average = fast_mean(spreads)` over the **bounded** window.
   `fast_mean([]) = 0.0` (lines 146-152). The pinned comment at lines 97-101 explains why
   incremental `fast_mean_iterated` is wrong at capacity: it subtracts the just-pushed
   spread rather than the evicted oldest one, freezing the mean.
6. **Varying-spread regression** (lines 279-300): 15 quotes with constant bid and asks
   `100.01..100.15` leave the last 10 spreads `0.06..0.15` and `average = 0.105`, not
   the stale `0.055`. Our mirror reproduces this exactly.
7. **Reset / display** (lines 46-61, 106-112): `reset()` zeroes `current`/`average` and
   clears the window and both flags; `Display` is `SpreadAnalyzer({capacity},{instrument_id})`.

**IEEE-754 note:** no NaN/Inf guards exist upstream. `sum::<f64>()` is a left-to-right sum;
the mirror uses plain `sum()`, deliberately **not** `math.fsum`, and `math.log(1.0 + x)`
rather than `log1p` in the probability functions, to preserve pinned numerics.

## 3. `nautilus_trader` — `ExitGate`: honest provenance finding

`PINS.md:12` and `ADR-0015:24` name `ExitGate` as an execution-parity target, but a
case-insensitive search of every `*.rs`, `*.py`, and `*.pyi` file in the pinned clone
(`crates/` + `python/`, 3,384 files) finds **no `ExitGate`, `exit_gate`, or `exit gate` symbol**.
This item is therefore recorded as **UPSTREAM_SYMBOL_UNVERIFIED**; inventing upstream
semantics for it would violate Charter rule 1.

The two verifiable pieces we do have:

* **Pinned nautilus exit primitive:** `ContingencyType` discriminants `OCO = 1`, `OTO = 2`,
  `OUO = 3` (`crates/model/src/enums.rs:609-616`); order builders attach OTO via
  `.contingency_type(ContingencyType::Oto)` (`crates/model/src/orders/builder.rs:748-752`);
  OTO parent linkage is checked in `crates/model/src/orders/mod.rs:469`.
* **Harness-enforced exit gate:** `src/cc_sota_harness/gates.py:21-33,45-81` — paper venues
  only (`PA`/`DU`), side-correct stop, `risk <= 2.00%` (`MAX_PROTECTIVE_STOP_PCT = 0.02`,
  line 15), RTH entries require an atomic broker OTO/bracket stop, extended-hours entries
  require an awake limit exit (or IBKR `outsideRth` stop), and 15 req/min of the paper budget
  is reserved for protective exits. `CLAUDE.md:14` states "no position exists without its exit."

`check_exit_gate()` delegates to `check_paper_order_intent()` so the two cannot drift,
then returns pinned `ContingencyType.OTO == 2`. This is a harness-side gate mapped onto a
verified nautilus primitive — **not** a claimed upstream `ExitGate` rule.

## 4. `hftbacktest` — queue-position fill rules (exact pinned rules)

### 4.1 Model surface and defaults

* `QueueModel` trait = `new_order`, `trade`, `depth`, `is_filled` (`queue.rs:24-40`).
* Python default is `LogProbQueueModel2` (`py-hftbacktest/src/lib.rs:113,142`); selectors for
  risk-averse, log, log2, power, power2, power3 and L3-FIFO live at lines 325-403.
* Replay-based exchange: no market impact; the order must be small relative to displayed size
  (`docs/order_fill.rst:8-18`). Accelerated mode that disables queue position is **not** parity:
  in that mode equality does not count (see `examples/Accelerated Backtesting.ipynb`).

### 4.2 `RiskAdverseQueueModel` (`queue.rs:42-96`)

1. `new_order`: `front_q_qty = bid/ask qty at the order's price tick` (lines 67-74).
2. `trade`: `front_q_qty -= traded_qty` (lines 76-79).
3. `depth`: `front_q_qty = min(front_q_qty, new_qty)` (lines 81-84) — cancellations/reductions
   happen at the tail, so depth changes never advance our queue; only trades do.
4. `is_filled`: `exec = round(-front_q_qty / lot_size) as i64`; if `exec > 0`, zero
   `front_q_qty` and return `exec * lot_size`, else `0.0` (lines 86-95).

### 4.3 `ProbQueueModel` (`queue.rs:98-217`)

1. `new_order`: `front_q_qty = side qty at tick`, `cum_trade_qty = 0` (lines 165-173).
2. `trade`: `front_q_qty -= qty`, `cum_trade_qty += qty` (lines 175-179).
3. `depth(prev, new)`: `chg = prev - new - cum_trade_qty`; reset `cum_trade_qty = 0`;
   if `chg < 0` then `front_q_qty = min(front_q_qty, new)` and stop (an increase cannot move
   the front). Else `front = front_q_qty`, `back = prev - front`, `p = prob(front, back)`
   (infinite `p` clamps to `1.0`), and
   `front_q_qty = min(front - (1-p)*chg + min(back - p*chg, 0), new)` (lines 181-205).
   Subtracting `cum_trade_qty` prevents double-counting trade-driven depth changes.
4. `is_filled`: identical lot-rounded core to §4.2 (lines 207-216).
5. Probability functions (lines 219-330), with `f(x) = x**n` or `f(x) = log(1+x)`:

| Function | `prob(front, back)` | Lines |
|---|---|---|
| `PowerProbQueueFunc` | `f(back) / (f(back) + f(front))` | 236-239 |
| `LogProbQueueFunc` | `f(back) / (f(back) + f(front))`, `f = log(1+x)` | 258-261 |
| `LogProbQueueFunc2` (default) | `f(back) / f(back + front)` | 280-283 |
| `PowerProbQueueFunc2` | `f(back) / f(back + front)` | 303-306 |
| `PowerProbQueueFunc3` | `1 - f(front / (front + back))` | 326-329 |

   Required endpoints (`docs/order_fill.rst:163-169`): `prob(0, ·) = 1` (front of queue ⇒ all
   decreases are behind us), `prob(·, 0) = 0` (tail ⇒ all decreases are ahead of us).

### 4.4 Exchange fill conditions

`NoPartialFillExchange` (`docs/order_fill.rst:25-44`; `nopartialfillexchange.rs:114-162,164-196,218-312,314-433`):

* Resting **buy**: full maker fill if `order_tick >= best_ask_tick`, or `order_tick > trade_tick`;
  on `order_tick == trade_tick`, call `queue_model.trade()` then fill only if `is_filled() > 0`.
  Resting **sell** is the mirror (`<= best_bid`, `< buy trade tick`).
* New limit with `GTC`/`FOK`/`IOC` that crosses the best is fully filled at the best as taker
  — FOK and IOC are treated identically because the fill is always complete; a crossing
  `GTX` post-only order **expires**. Non-crossing `FOK`/`IOC` also expire; non-crossing
  `GTC`/`GTX` post to the book and call `new_order()` to initialize queue position.
* Market orders and liquidity-taking orders fill fully at the best **regardless of the quantity
  displayed at the best**; no partial fills in this mode.
* Depth changes call `queue_model.depth()` only for resting orders at that exact tick
  (lines 218-240); best-price crossings fill all orders on the affected ticks (lines 242-312).

`PartialFillExchange` (`docs/order_fill.rst:53-92`; `partialfillexchange.rs:39-76,130-206,208-244`):

* Same strict-cross full-fill rules; at equal price, `exec_qty = min(is_filled(), leaves_qty)`,
  capped at remaining size. If `is_filled() > leaves_qty`, the order is fully filled.
* Status is `PartiallyFilled` when `round(leaves_qty / lot_size) > 0`, else `Filled`.

**Rounding hazard (verified):** Rust `f64::round()` rounds halves **away from zero**, while
Python's built-in `round()` is banker's rounding. `-2.5 / 1.0` must yield `exec = 3` lots, not
`2`. The mirror uses `rust_round()` and a property test pins this behavior.

`L3FIFOQueueModel` (`queue.rs:332-489`): with Market-By-Order data, all orders are held in a
FIFO at price-time priority; a clear message clears all backtest orders (lines 455-470), which
is a deliberate upstream deviation requiring reason code in any live-vs-backtest comparison.

## 5. Failure modes, non-goals, rollback

* **Non-goals:** no live-order routing, no market-impact simulation, no study-wall data use,
  no modification of pinned upstreams, no claim that a nautilus `ExitGate` symbol exists.
* **Failure modes:** frozen rolling mean (SpreadAnalyzer incremental trap), optimistic queue
  advancement (using `ProbQueueModel` where risk-averse is warranted), double-counted trade
  quantity in `depth()`, banker's-rounding fill drift, and treating equality as a fill when
  queue position is disabled.
* **Rollback:** delete the three owned files and release the `sota-bus` lease; no shared
  state, pins, ADRs, or upstream clones were changed.
* **Gate before merge:** `mise exec -- uv run pytest -v`, `mise exec -- ruff check .`;
  no `scripts/merge_gate.py` exists in this worktree.

## 6. Verification witness

```bash
mise exec -- uv run pytest -v     # 53 passed, 4 pandas upstream warnings, 5.95s (Python 3.14.10 / pytest 9.2.0)
mise exec -- ruff check .         # 0 errors after UP042 fix (Side/FillOutcome now enum.StrEnum)
```

The same counts are mirrored to the `cc-sota-harness` clock-out handover on `sota-bus`.
The 4 warnings originate in the pre-existing `pandas` dependency inside
`tests/test_sota_ecosystem.py::test_t1_t4_quant_stack_e2e`, not in this parity work.
