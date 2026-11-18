"""Executable parity reference for the pinned upstream execution rules (ADR-0015 Move #3).

Every rule below is transcribed from the read-only clones in ``~/Documents/upstream/``
at the exact pins recorded in ``PINS.md``. Nothing is imported from, or written to,
those clones. File/line citations refer to those checked-out commits:

* ``nautilus_trader`` ``da6b57aefdd62b44f675e434ffcfefca7f4025dd`` (tag ``v2.0.0rc9``):
  ``crates/indicators/src/ratio/spread_analyzer.rs``,
  ``crates/model/src/enums.rs``, ``crates/model/src/orders/builder.rs``.
* ``hftbacktest`` ``5f3ec40b2afb764e0fea112f941ed85523ef4e88``:
  ``hftbacktest/src/backtest/models/queue.rs``,
  ``hftbacktest/src/backtest/proc/{no,partial}partialfillexchange.rs``,
  ``py-hftbacktest/src/lib.rs``, ``docs/order_fill.rst``.

The ``ExitGate`` name appears in ``PINS.md``/``ADR-0015`` but has **no symbol** in the
pinned nautilus clone. The exit gate here is therefore the harness-side ADR-0022 gate
(``gates.check_paper_order_intent``) mapped onto the pinned nautilus OTO contingency;
see ``docs/reports/UPSTREAM_EXECUTION_PARITY_SPEC.md`` for the honest provenance note.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum, StrEnum

from cc_sota_harness.gates import OrderIntent, check_paper_order_intent

NAUTILUS_PIN = "da6b57aefdd62b44f675e434ffcfefca7f4025dd"
HFTBACKTEST_PIN = "5f3ec40b2afb764e0fea112f941ed85523ef4e88"

# ---------------------------------------------------------------------------
# nautilus_trader: SpreadAnalyzer
# ---------------------------------------------------------------------------


class SpreadAnalyzerParity:
    """Python mirror of pinned ``SpreadAnalyzer`` (spread_analyzer.rs:36-152).

    Deliberately reproduces the pinned initialization timing: ``initialized`` is
    flipped *before* the quote is pushed, so with capacity ``n > 0`` it becomes
    true on the ``(n + 1)``-th accepted quote, not on the ``n``-th.
    """

    def __init__(self, capacity: int, instrument_id: str) -> None:
        # new_checked uses try_reserve_exact(capacity) (spread_analyzer.rs:128-143).
        if capacity < 0:
            raise ValueError("capacity must be non-negative; a zero capacity is accepted")
        if capacity > sys.maxsize // 8:
            raise MemoryError(
                "memory allocation failed because the computed capacity exceeded the collection's maximum"
            )
        self.capacity = capacity
        self.instrument_id = instrument_id
        self.current = 0.0
        self.average = 0.0
        self.initialized = False
        self.has_inputs = False
        self._spreads: list[float] = []

    def handle_quote(self, instrument_id: str, bid: float, ask: float) -> None:
        """Mirror ``Indicator::handle_quote`` (spread_analyzer.rs:70-104)."""
        if instrument_id != self.instrument_id:  # line 71-73: foreign instruments ignored
            return

        if not self.initialized:  # lines 75-82: check happens before push
            self.has_inputs = True
            if len(self._spreads) == self.capacity:
                self.initialized = True

        spread = ask - bid  # line 86: raw f64 subtraction, no rounding or tick conversion
        self.current = spread  # line 88
        self._spreads.append(spread)  # line 89
        if len(self._spreads) > self.capacity:  # lines 91-95: FIFO eviction, O(capacity)
            self._spreads.pop(0)
        # lines 97-102: recompute from the bounded window; never incremental,
        # because incremental subtraction at capacity subtracts the just-pushed value.
        values = self._spreads
        self.average = sum(values) / len(values) if values else 0.0

    def reset(self) -> None:
        """Mirror ``Indicator::reset`` (spread_analyzer.rs:106-112)."""
        self.current = 0.0
        self.average = 0.0
        self._spreads.clear()
        self.initialized = False
        self.has_inputs = False

    @property
    def window(self) -> tuple[float, ...]:
        """Read-only view of the bounded rolling window (for assertions)."""
        return tuple(self._spreads)

    def __str__(self) -> str:
        """Mirror ``Display`` via ``name()`` (spread_analyzer.rs:46-61)."""
        return f"SpreadAnalyzer({self.capacity},{self.instrument_id})"


# ---------------------------------------------------------------------------
# nautilus_trader: exit-gate contingency primitives + harness ADR-0022 gate
# ---------------------------------------------------------------------------


class ContingencyType(IntEnum):
    """Pinned nautilus ``ContingencyType`` discriminants (enums.rs:609-616)."""

    OCO = 1
    OTO = 2
    OUO = 3


EXIT_CONTINGENCY = ContingencyType.OTO  # broker-attached OTO bracket stop


@dataclass(frozen=True)
class ExitGateIntent:
    """Inputs to the no-position-without-exit gate (ADR-0022 / gates.py:21-33)."""

    venue_prefix: str
    side: str
    entry_price: float
    stop_price: float
    session: str
    has_broker_oto_stop: bool
    has_awake_limit_exit: bool
    requests_used_last_min: int = 0


def check_exit_gate(intent: ExitGateIntent) -> ContingencyType:
    """Fail-closed exit gate; delegates to the harness gate so rules cannot drift.

    Returns the pinned nautilus contingency type that expresses the exit link
    (``ContingencyType::Oto == 2``; crates/model/src/orders/builder.rs:748-752).
    """
    check_paper_order_intent(
        OrderIntent(
            venue_prefix=intent.venue_prefix,
            symbol="ABCD",
            side=intent.side,
            entry_price=intent.entry_price,
            stop_price=intent.stop_price,
            session=intent.session,
            has_broker_oto_stop=intent.has_broker_oto_stop,
            has_awake_limit_exit=intent.has_awake_limit_exit,
            requests_used_last_min=intent.requests_used_last_min,
        )
    )
    return EXIT_CONTINGENCY


# ---------------------------------------------------------------------------
# hftbacktest: queue-position models
# ---------------------------------------------------------------------------


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class QueuePos:
    """Pinned ``QueuePos`` state (queue.rs:98-122)."""

    front_q_qty: float = 0.0
    cum_trade_qty: float = 0.0


def ieee_div(a: float, b: float) -> float:
    """Rust ``f64`` division semantics (no ZeroDivisionError) for probability math."""
    if b != 0.0:
        return a / b
    if a == 0.0 or math.isnan(a):
        return math.nan
    return math.copysign(math.inf, math.copysign(1.0, a) * math.copysign(1.0, b))


def rust_round(x: float) -> int:
    """Rust ``f64::round()``: halves round away from zero (Python ``round`` is banker's)."""
    return math.floor(x + 0.5) if x >= 0.0 else math.ceil(x - 0.5)


def _filled_qty(front_q_qty: float, lot_size: float) -> float:
    """Shared ``is_filled`` core (queue.rs:86-95 and 207-216)."""
    if lot_size <= 0.0:
        raise ValueError("lot_size must be strictly positive")
    exec_lots = rust_round(-front_q_qty / lot_size)
    return exec_lots * lot_size if exec_lots > 0 else 0.0


class RiskAdverseQueueModel:
    """Most conservative model (queue.rs:42-96): cancellation/modification at the tail.

    Queue position advances *only* on trades at the same price level.
    """

    def new_order(self, resting_qty: float) -> QueuePos:
        return QueuePos(front_q_qty=resting_qty)  # queue.rs:67-74

    def trade(self, q: QueuePos, qty: float) -> None:
        q.front_q_qty -= qty  # queue.rs:76-79

    def depth(self, q: QueuePos, prev_qty: float, new_qty: float) -> None:
        q.front_q_qty = min(q.front_q_qty, new_qty)  # queue.rs:81-84

    def is_filled(self, q: QueuePos, lot_size: float) -> float:
        exec_qty = _filled_qty(q.front_q_qty, lot_size)
        if exec_qty > 0.0:  # queue.rs:88-95: q is zeroed after a fill
            q.front_q_qty = 0.0
        return exec_qty


class ProbQueueModel:
    """Probability-based model (queue.rs:98-217) with pinned update equations."""

    def __init__(self, probability: Callable[[float, float], float]) -> None:
        self.probability = probability

    def new_order(self, resting_qty: float) -> QueuePos:
        return QueuePos(front_q_qty=resting_qty)  # queue.rs:165-173

    def trade(self, q: QueuePos, qty: float) -> None:
        q.front_q_qty -= qty  # queue.rs:175-179
        q.cum_trade_qty += qty

    def depth(self, q: QueuePos, prev_qty: float, new_qty: float) -> None:
        # queue.rs:181-205
        chg = prev_qty - new_qty
        chg -= q.cum_trade_qty  # avoid double counting trade-driven depth changes
        q.cum_trade_qty = 0.0
        if chg < 0.0:  # a quantity increase never moves the front
            q.front_q_qty = min(q.front_q_qty, new_qty)
            return
        front = q.front_q_qty
        back = prev_qty - front
        prob = self.probability(front, back)
        if math.isinf(prob):  # queue.rs:199-201
            prob = 1.0
        est_front = front - (1.0 - prob) * chg + min(back - prob * chg, 0.0)
        q.front_q_qty = min(est_front, new_qty)

    def is_filled(self, q: QueuePos, lot_size: float) -> float:
        exec_qty = _filled_qty(q.front_q_qty, lot_size)
        if exec_qty > 0.0:  # queue.rs:207-216
            q.front_q_qty = 0.0
        return exec_qty


# Probability functions (queue.rs:219-330). f = log(1 + x) uses log(1+x), NOT log1p,
# to match the pinned Rust expression bit-for-bit in normal ranges.
ProbabilityFn = Callable[[float, float], float]


def power_prob_queue_func(n: float) -> ProbabilityFn:
    def f(x: float) -> float:
        return x**n

    def prob(front: float, back: float) -> float:
        return ieee_div(f(back), f(back) + f(front))  # queue.rs:236-239

    return prob


def log_prob_queue_func() -> ProbabilityFn:
    def f(x: float) -> float:
        return math.log(1.0 + x)

    def prob(front: float, back: float) -> float:
        return ieee_div(f(back), f(back) + f(front))  # queue.rs:258-261

    return prob


def log_prob_queue_func2() -> ProbabilityFn:
    def f(x: float) -> float:
        return math.log(1.0 + x)

    def prob(front: float, back: float) -> float:
        return ieee_div(f(back), f(back + front))  # queue.rs:280-283

    return prob


def power_prob_queue_func2(n: float) -> ProbabilityFn:
    def f(x: float) -> float:
        return x**n

    def prob(front: float, back: float) -> float:
        return ieee_div(f(back), f(back + front))  # queue.rs:303-306

    return prob


def power_prob_queue_func3(n: float) -> ProbabilityFn:
    def f(x: float) -> float:
        return x**n

    def prob(front: float, back: float) -> float:
        return 1.0 - f(ieee_div(front, front + back))  # queue.rs:326-329

    return prob


DEFAULT_QUEUE_MODEL_FACTORY = log_prob_queue_func2  # py-hftbacktest/src/lib.rs:142


# ---------------------------------------------------------------------------
# hftbacktest: exchange fill conditions
# ---------------------------------------------------------------------------


class FillOutcome(StrEnum):
    NONE = "none"
    FULL_MAKER = "full_maker"
    FULL_TAKER = "full_taker"
    EXPIRED_POST_ONLY = "expired_post_only"
    PARTIAL = "partial"


def crosses_best(order_tick: int, best_opposite_tick: int, side: Side) -> bool:
    """Marketable limit test (nopartialfillexchange.rs:322-323 and 379-380)."""
    return order_tick >= best_opposite_tick if side is Side.BUY else order_tick <= best_opposite_tick


def resting_trade_fill(
    side: Side, order_tick: int, trade_tick: int, front_q_qty: float, lot_size: float, *, partial: bool = False
) -> FillOutcome:
    """Fill decision for a resting order when a trade prints at ``trade_tick``.

    NoPartialFillExchange (nopartialfillexchange.rs:114-162): a strictly better
    price fills in full; equal price only after the queue model reports a fill.
    PartialFillExchange (partialfillexchange.rs:130-206) uses the same decision
    but reports ``PARTIAL`` so the caller can cap execution at ``leaves_qty``.

    ``front_q_qty`` is the queue state *after* ``queue_model.trade()`` has been
    applied for the printed trade; that call is the caller's responsibility.
    """
    if side is Side.BUY:
        if order_tick > trade_tick:
            return FillOutcome.FULL_MAKER
        if order_tick < trade_tick:
            return FillOutcome.NONE
    else:
        if order_tick < trade_tick:
            return FillOutcome.FULL_MAKER
        if order_tick > trade_tick:
            return FillOutcome.NONE

    if _filled_qty(front_q_qty, lot_size) > 0.0:
        return FillOutcome.PARTIAL if partial else FillOutcome.FULL_MAKER
    return FillOutcome.NONE


def ack_new_limit(side: Side, order_tick: int, best_opposite_tick: int, time_in_force: str) -> tuple[FillOutcome, bool]:
    """Admission rule for a new limit order; returns (outcome, posts_to_book).

    Mirrors nopartialfillexchange.rs:314-433. Marketable ``GTC``/``FOK``/``IOC``
    take liquidity fully at the best price (even FOK/IOC); ``GTX`` post-only
    expires instead. Non-marketable ``FOK``/``IOC`` also expire.
    """
    if time_in_force not in {"GTC", "GTX", "FOK", "IOC"}:
        raise ValueError(f"unsupported time_in_force '{time_in_force}'")
    if crosses_best(order_tick, best_opposite_tick, side):
        if time_in_force == "GTX":
            return FillOutcome.EXPIRED_POST_ONLY, False
        return FillOutcome.FULL_TAKER, False
    if time_in_force in {"FOK", "IOC"}:
        return FillOutcome.EXPIRED_POST_ONLY, False
    return FillOutcome.NONE, True  # rest on book; queue model new_order() is called


def partial_execution(front_q_qty: float, lot_size: float, leaves_qty: float) -> tuple[float, str]:
    """PartialFillExchange quantity/status rule (partialfillexchange.rs:147-162, 208-236)."""
    filled_qty = _filled_qty(front_q_qty, lot_size)
    if filled_qty <= 0.0:
        return 0.0, "New"
    exec_qty = min(filled_qty, leaves_qty)
    remaining = leaves_qty - exec_qty
    status = "Filled" if remaining <= 0.0 or rust_round(remaining / lot_size) <= 0 else "PartiallyFilled"
    return exec_qty, status
