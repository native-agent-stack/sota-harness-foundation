"""Unit tests for ADR-0015 Move #3: exact pinned upstream execution parity (E3 witness).

Every behavioral assertion below is transcribed from a file/line in
``docs/reports/UPSTREAM_EXECUTION_PARITY_SPEC.md`` and enforced against the read-only
pinned clones under ``~/Documents/upstream/``.
"""

from __future__ import annotations

import math
import pathlib
import subprocess
from collections.abc import Callable
from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cc_sota_harness.gates import OrderIntent, check_paper_order_intent
from cc_sota_harness.upstream_execution_parity import (
    DEFAULT_QUEUE_MODEL_FACTORY,
    EXIT_CONTINGENCY,
    HFTBACKTEST_PIN,
    NAUTILUS_PIN,
    ContingencyType,
    ExitGateIntent,
    FillOutcome,
    ProbQueueModel,
    QueuePos,
    RiskAdverseQueueModel,
    Side,
    SpreadAnalyzerParity,
    ack_new_limit,
    check_exit_gate,
    ieee_div,
    log_prob_queue_func,
    log_prob_queue_func2,
    partial_execution,
    power_prob_queue_func,
    power_prob_queue_func2,
    power_prob_queue_func3,
    resting_trade_fill,
    rust_round,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
UPSTREAM = pathlib.Path.home() / "Documents" / "upstream"
SPEC = REPO_ROOT / "docs" / "reports" / "UPSTREAM_EXECUTION_PARITY_SPEC.md"
INSTRUMENT = "ETHUSDT-PERP.BINANCE"


# ---------------------------------------------------------------------------
# Provenance guards (E3: pins and honesty claim re-verified every run)
# ---------------------------------------------------------------------------


def test_spec_doc_records_pins_and_exitgate_provenance() -> None:
    text = SPEC.read_text()
    assert NAUTILUS_PIN in text
    assert HFTBACKTEST_PIN in text
    assert "UPSTREAM_SYMBOL_UNVERIFIED" in text
    assert "da6b57aefdd62b44f675e434ffcfefca7f4025dd" in text
    assert "5f3ec40b2afb764e0fea112f941ed85523ef4e88" in text


@pytest.mark.skipif(
    not (UPSTREAM / "nautilus_trader").is_dir() or not (UPSTREAM / "hftbacktest").is_dir(),
    reason="Local ~/Documents/upstream clones not mounted on cloud CI runner",
)
@pytest.mark.parametrize(
    ("repo", "pin"),
    [("nautilus_trader", NAUTILUS_PIN), ("hftbacktest", HFTBACKTEST_PIN)],
)
def test_pinned_clone_head_matches_spec_and_is_clean(repo: str, pin: str) -> None:
    clone = UPSTREAM / repo
    head = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(clone), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout
    assert head == pin, f"{repo} moved off pin: {head}"
    assert status == "", f"{repo} worktree is dirty (read-only boundary violated)"


@pytest.mark.skipif(
    not (UPSTREAM / "nautilus_trader").is_dir(),
    reason="Local ~/Documents/upstream/nautilus_trader clone not mounted on cloud CI runner",
)
def test_pinned_nautilus_really_has_no_exitgate_symbol() -> None:
    """Enforces the honest provenance finding; update this test only with a new pin."""
    clone = UPSTREAM / "nautilus_trader"
    needles = (b"exitgate", b"exit_gate", b"exit gate")
    scanned = 0
    for root in (clone / "crates", clone / "python"):
        for path in root.rglob("*"):
            if path.suffix not in {".rs", ".py", ".pyi"} or not path.is_file():
                continue
            scanned += 1
            lowered = path.read_bytes().lower()
            for needle in needles:
                assert needle not in lowered, f"unexpected {needle!r} in pinned clone at {path}"
    assert scanned > 1000, "source scan was too small to support the provenance claim"


# ---------------------------------------------------------------------------
# SpreadAnalyzer parity (pinned spread_analyzer.rs:36-152)
# ---------------------------------------------------------------------------


def test_spread_analyzer_initialization_and_bounded_rolling_mean() -> None:
    indicator = SpreadAnalyzerParity(capacity=10, instrument_id=INSTRUMENT)
    assert str(indicator) == f"SpreadAnalyzer(10,{INSTRUMENT})"
    assert not indicator.has_inputs and not indicator.initialized

    # Pinned tests feed 9/10 quotes and assert still uninitialized (lines 200-218).
    for i in range(1, 11):
        indicator.handle_quote(INSTRUMENT, bid=100.0, ask=100.0 + 0.01 * i)
        if i < 10:
            assert not indicator.initialized
        if i == 1:
            assert indicator.has_inputs
    assert len(indicator.window) == 10
    assert not indicator.initialized  # len == capacity is checked before the 10th push
    assert indicator.current == pytest.approx(0.10)
    assert indicator.average == pytest.approx(0.055, abs=1e-9)  # mean of 0.01..0.10

    for i in range(11, 16):
        indicator.handle_quote(INSTRUMENT, bid=100.0, ask=100.0 + 0.01 * i)
    assert indicator.initialized
    assert len(indicator.window) == 10  # FIFO eviction, never unbounded
    assert indicator.window == pytest.approx(tuple(0.01 * i for i in range(6, 16)))
    assert indicator.average == pytest.approx(0.105, abs=1e-9)  # pinned lines 279-300


def test_spread_analyzer_zero_capacity_foreign_quote_and_reset() -> None:
    zero = SpreadAnalyzerParity(capacity=0, instrument_id=INSTRUMENT)
    zero.handle_quote("OTHER.NASDAQ", bid=10.0, ask=10.5)
    assert not zero.has_inputs and not zero.initialized and zero.window == ()
    zero.handle_quote(INSTRUMENT, bid=10.0, ask=10.5)
    assert zero.has_inputs and zero.initialized
    assert zero.current == pytest.approx(0.5)
    assert zero.average == 0.0  # push then evict leaves fast_mean([]) == 0.0
    assert zero.window == ()

    zero.reset()
    assert zero.current == 0.0 and zero.average == 0.0
    assert not zero.initialized and not zero.has_inputs and zero.window == ()


@given(
    spreads=st.lists(
        st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=24,
    ),
    capacity=st.integers(min_value=1, max_value=8),
)
def test_property_spread_analyzer_matches_bounded_mean(spreads: list[float], capacity: int) -> None:
    indicator = SpreadAnalyzerParity(capacity=capacity, instrument_id=INSTRUMENT)
    for spread in spreads:
        indicator.handle_quote(INSTRUMENT, bid=100.0, ask=100.0 + spread)
    expected = spreads[-capacity:]
    assert list(indicator.window) == pytest.approx(expected)
    assert indicator.average == pytest.approx(sum(expected) / len(expected))
    assert indicator.initialized is (len(spreads) > capacity)


# ---------------------------------------------------------------------------
# ExitGate parity (honest harness gate -> pinned OTO contingency == 2)
# ---------------------------------------------------------------------------


def test_exit_gate_uses_pinned_oto_discriminant() -> None:
    assert ContingencyType.OCO == 1
    assert ContingencyType.OTO == 2
    assert ContingencyType.OUO == 3
    assert EXIT_CONTINGENCY is ContingencyType.OTO


def test_exit_gate_is_fail_closed_and_delegates_to_harness_gate() -> None:
    valid = ExitGateIntent(
        venue_prefix="PA",
        side="buy",
        entry_price=10.0,
        stop_price=9.85,
        session="rth",
        has_broker_oto_stop=True,
        has_awake_limit_exit=False,
    )
    assert check_exit_gate(valid) is ContingencyType.OTO

    no_exit = replace(valid, has_broker_oto_stop=False)
    with pytest.raises(ValueError, match="requires atomic broker OTO"):
        check_exit_gate(no_exit)
    with pytest.raises(ValueError, match="requires atomic broker OTO"):
        check_paper_order_intent(
            OrderIntent(
                venue_prefix="PA",
                symbol="ABCD",
                side="buy",
                entry_price=10.0,
                stop_price=9.85,
                session="rth",
                has_broker_oto_stop=False,
                has_awake_limit_exit=False,
                requests_used_last_min=0,
            )
        )

    wide_stop = replace(valid, stop_price=9.70)
    with pytest.raises(ValueError, match="exceeds 2.00%"):
        check_exit_gate(wide_stop)

    extended = replace(valid, session="overnight", has_broker_oto_stop=False, has_awake_limit_exit=True)
    assert check_exit_gate(extended) is ContingencyType.OTO
    naked_overnight = replace(extended, has_awake_limit_exit=False)
    with pytest.raises(ValueError, match="requires awake extended-hours limit exit"):
        check_exit_gate(naked_overnight)


# ---------------------------------------------------------------------------
# hftbacktest queue models (pinned queue.rs:24-330)
# ---------------------------------------------------------------------------


def test_rust_round_half_away_from_zero_not_bankers() -> None:
    assert rust_round(2.5) == 3
    assert rust_round(-2.5) == -3
    assert rust_round(1.5) == 2
    assert rust_round(1.4) == 1
    assert round(2.5) == 2  # Python's built-in differs; the mirror must not use it
    q = QueuePos(front_q_qty=-2.5)
    assert RiskAdverseQueueModel().is_filled(q, lot_size=1.0) == 3.0
    assert q.front_q_qty == 0.0


def test_risk_adverse_queue_advances_only_on_trades() -> None:
    model = RiskAdverseQueueModel()
    q = model.new_order(resting_qty=10.0)
    assert q.front_q_qty == 10.0
    model.depth(q, prev_qty=10.0, new_qty=7.0)  # tail cancellation: min(10, 7)
    assert q.front_q_qty == 7.0
    model.trade(q, qty=3.0)
    assert q.front_q_qty == 4.0
    assert model.is_filled(q, lot_size=1.0) == 0.0
    model.trade(q, qty=5.0)  # front == -1.0
    assert model.is_filled(q, lot_size=1.0) == 1.0
    assert q.front_q_qty == 0.0


def test_prob_queue_model_exact_depth_and_trade_dedup() -> None:
    model = ProbQueueModel(lambda front, back: 0.5)
    q = model.new_order(resting_qty=70.0)
    model.trade(q, qty=0.0)
    # chg = 100 - 90 = 10; front=70, back=30, p=0.5 -> 70 - 0.5*10 + min(30-5,0) = 65
    model.depth(q, prev_qty=100.0, new_qty=90.0)
    assert q.front_q_qty == pytest.approx(65.0)
    assert q.cum_trade_qty == 0.0

    model.trade(q, qty=4.0)
    assert (q.front_q_qty, q.cum_trade_qty) == pytest.approx((61.0, 4.0))
    # raw chg=4, minus cum_trade_qty=4 -> 0: the trade already moved the book, no re-advance
    model.depth(q, prev_qty=90.0, new_qty=86.0)
    assert q.front_q_qty == pytest.approx(61.0)
    assert q.cum_trade_qty == 0.0

    q2 = model.new_order(resting_qty=70.0)
    model.depth(q2, prev_qty=70.0, new_qty=90.0)  # quantity increase -> min(front, new)
    assert q2.front_q_qty == pytest.approx(70.0)

    inf_model = ProbQueueModel(lambda front, back: math.inf)
    q3 = inf_model.new_order(resting_qty=70.0)
    inf_model.depth(q3, prev_qty=100.0, new_qty=90.0)  # inf probability clamps to 1.0
    assert q3.front_q_qty == pytest.approx(70.0)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: power_prob_queue_func(2.0),
        log_prob_queue_func,
        log_prob_queue_func2,
        lambda: power_prob_queue_func2(2.0),
        lambda: power_prob_queue_func3(2.0),
    ],
)
def test_probability_functions_respect_pinned_endpoints(
    factory: Callable[[], Callable[[float, float], float]],
) -> None:
    prob = factory()
    assert prob(0.0, 10.0) == pytest.approx(1.0)  # head of queue: all decreases behind us
    assert prob(10.0, 0.0) == pytest.approx(0.0)  # tail: all decreases ahead of us
    assert 0.0 <= prob(4.0, 6.0) <= 1.0


def test_default_probability_model_is_log2_not_log1() -> None:
    assert DEFAULT_QUEUE_MODEL_FACTORY is log_prob_queue_func2
    default = DEFAULT_QUEUE_MODEL_FACTORY()
    assert default(4.0, 6.0) == pytest.approx(log_prob_queue_func2()(4.0, 6.0))
    assert default(4.0, 6.0) != pytest.approx(log_prob_queue_func()(4.0, 6.0))


def test_ieee_division_matches_rust_instead_of_raising() -> None:
    assert ieee_div(1.0, 0.0) == math.inf
    assert ieee_div(-1.0, 0.0) == -math.inf
    assert math.isnan(ieee_div(0.0, 0.0))


@given(
    front=st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    raw_chg=st.floats(min_value=1.0, max_value=20.0, allow_nan=False, allow_infinity=False),
    prob=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_property_prob_depth_decrease_never_advances_past_front(front: float, raw_chg: float, prob: float) -> None:
    model = ProbQueueModel(lambda _front, _back: prob)
    q = model.new_order(resting_qty=front)
    new_qty = front + raw_chg  # back == raw_chg, no clamp expected
    model.depth(q, prev_qty=front + raw_chg + raw_chg, new_qty=new_qty)
    assert q.front_q_qty <= front + 1e-9


# ---------------------------------------------------------------------------
# Exchange fill conditions (pinned docs/order_fill.rst + proc/*.rs)
# ---------------------------------------------------------------------------


def test_resting_fill_conditions_strict_price_improvement_and_queue_front() -> None:
    # Buy: order price > sell trade price fills; < does not; == needs queue exhaustion.
    assert resting_trade_fill(Side.BUY, 101, 100, 5.0, 1.0) is FillOutcome.FULL_MAKER
    assert resting_trade_fill(Side.BUY, 99, 100, -5.0, 1.0) is FillOutcome.NONE
    assert resting_trade_fill(Side.BUY, 100, 100, 5.0, 1.0) is FillOutcome.NONE
    assert resting_trade_fill(Side.BUY, 100, 100, -1.0, 1.0) is FillOutcome.FULL_MAKER
    # Sell is the mirror.
    assert resting_trade_fill(Side.SELL, 99, 100, 5.0, 1.0) is FillOutcome.FULL_MAKER
    assert resting_trade_fill(Side.SELL, 101, 100, -5.0, 1.0) is FillOutcome.NONE
    assert resting_trade_fill(Side.SELL, 100, 100, 5.0, 1.0) is FillOutcome.NONE
    assert resting_trade_fill(Side.SELL, 100, 100, -1.0, 1.0) is FillOutcome.FULL_MAKER


def test_partial_exchange_equal_price_reports_partial() -> None:
    assert resting_trade_fill(Side.BUY, 100, 100, -1.0, 1.0, partial=True) is FillOutcome.PARTIAL
    assert resting_trade_fill(Side.BUY, 100, 100, 1.0, 1.0, partial=True) is FillOutcome.NONE


def test_ack_new_limit_marketable_taker_post_only_and_ioc_rules() -> None:
    for tif in ("GTC", "FOK", "IOC"):
        assert ack_new_limit(Side.BUY, 101, 100, tif) == (FillOutcome.FULL_TAKER, False)
        assert ack_new_limit(Side.SELL, 99, 100, tif) == (FillOutcome.FULL_TAKER, False)
    assert ack_new_limit(Side.BUY, 101, 100, "GTX") == (FillOutcome.EXPIRED_POST_ONLY, False)
    assert ack_new_limit(Side.BUY, 99, 100, "GTC") == (FillOutcome.NONE, True)
    assert ack_new_limit(Side.BUY, 99, 100, "GTX") == (FillOutcome.NONE, True)
    assert ack_new_limit(Side.BUY, 99, 100, "FOK") == (FillOutcome.EXPIRED_POST_ONLY, False)
    with pytest.raises(ValueError, match="unsupported time_in_force"):
        ack_new_limit(Side.BUY, 99, 100, "BOGUS")


def test_partial_execution_caps_at_leaves_and_status_uses_rust_rounding() -> None:
    assert partial_execution(front_q_qty=-10.0, lot_size=1.0, leaves_qty=4.0) == (4.0, "Filled")
    assert partial_execution(front_q_qty=-4.0, lot_size=1.0, leaves_qty=10.0) == (4.0, "PartiallyFilled")
    assert partial_execution(front_q_qty=-4.0, lot_size=1.0, leaves_qty=4.4) == (
        4.0,
        "Filled",
    )  # 0.4 lot rounds to 0
    assert partial_execution(front_q_qty=5.0, lot_size=1.0, leaves_qty=10.0) == (0.0, "New")
