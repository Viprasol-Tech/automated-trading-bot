"""Tests for :mod:`automated_trading_bot.strategy`."""

from __future__ import annotations

import pytest

from automated_trading_bot.config import BotConfig
from automated_trading_bot.models import Signal
from automated_trading_bot.strategy import (
    STRATEGIES,
    BreakoutStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    Strategy,
    build_strategy,
    rolling_std,
    simple_moving_average,
)


def test_simple_moving_average_known_value() -> None:
    assert simple_moving_average([1.0, 2.0, 3.0, 4.0], window=2) == 3.5
    assert simple_moving_average([1.0, 2.0, 3.0, 4.0], window=4) == 2.5


def test_sma_rejects_bad_window() -> None:
    with pytest.raises(ValueError):
        simple_moving_average([1.0, 2.0], window=0)
    with pytest.raises(ValueError):
        simple_moving_average([1.0, 2.0], window=5)


def test_rolling_std_known_value() -> None:
    # Population std of [2, 4, 4, 4, 5, 5, 7, 9] is 2.0.
    assert rolling_std([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0], window=8) == pytest.approx(2.0)


def test_rolling_std_flat_window_is_zero() -> None:
    assert rolling_std([5.0, 5.0, 5.0], window=3) == 0.0


def test_rolling_std_rejects_bad_window() -> None:
    with pytest.raises(ValueError):
        rolling_std([1.0], window=0)
    with pytest.raises(ValueError):
        rolling_std([1.0], window=4)


def test_flat_until_enough_history() -> None:
    strat = MomentumStrategy(fast=2, slow=4)
    assert strat.on_price(10.0) is Signal.FLAT
    assert strat.on_price(10.0) is Signal.FLAT
    assert strat.on_price(10.0) is Signal.FLAT  # only 3 of 4 bars


def test_uptrend_gives_buy() -> None:
    strat = MomentumStrategy(fast=2, slow=4)
    last = Signal.FLAT
    for price in [1.0, 2.0, 3.0, 4.0, 5.0]:
        last = strat.on_price(price)
    # Rising series -> fast SMA above slow SMA -> BUY.
    assert last is Signal.BUY


def test_downtrend_gives_sell() -> None:
    strat = MomentumStrategy(fast=2, slow=4)
    last = Signal.FLAT
    for price in [5.0, 4.0, 3.0, 2.0, 1.0]:
        last = strat.on_price(price)
    assert last is Signal.SELL


def test_constructor_requires_slow_gt_fast() -> None:
    with pytest.raises(ValueError, match="slow"):
        MomentumStrategy(fast=5, slow=5)


def test_momentum_satisfies_protocol() -> None:
    assert isinstance(MomentumStrategy(fast=2, slow=4), Strategy)


# --- Mean reversion -------------------------------------------------------


def test_mean_reversion_flat_until_window_full() -> None:
    strat = MeanReversionStrategy(window=4, threshold=1.0)
    assert strat.on_price(100.0) is Signal.FLAT
    assert strat.on_price(100.0) is Signal.FLAT
    assert strat.on_price(100.0) is Signal.FLAT


def test_mean_reversion_buys_oversold() -> None:
    strat = MeanReversionStrategy(window=4, threshold=0.5)
    # Build a baseline then drop sharply below the mean -> BUY.
    for price in [100.0, 100.0, 100.0]:
        strat.on_price(price)
    assert strat.on_price(80.0) is Signal.BUY


def test_mean_reversion_sells_overbought() -> None:
    strat = MeanReversionStrategy(window=4, threshold=0.5)
    for price in [100.0, 100.0, 100.0]:
        strat.on_price(price)
    assert strat.on_price(120.0) is Signal.SELL


def test_mean_reversion_flat_inside_band() -> None:
    strat = MeanReversionStrategy(window=4, threshold=3.0)
    for price in [100.0, 101.0, 99.0]:
        strat.on_price(price)
    assert strat.on_price(100.5) is Signal.FLAT


def test_mean_reversion_rejects_bad_args() -> None:
    with pytest.raises(ValueError, match="window"):
        MeanReversionStrategy(window=1)
    with pytest.raises(ValueError, match="threshold"):
        MeanReversionStrategy(window=4, threshold=0.0)


# --- Breakout -------------------------------------------------------------


def test_breakout_buys_new_high() -> None:
    strat = BreakoutStrategy(window=3)
    strat.on_price(10.0)
    strat.on_price(11.0)
    assert strat.on_price(12.0) is Signal.BUY  # new high over the channel


def test_breakout_sells_new_low() -> None:
    strat = BreakoutStrategy(window=3)
    strat.on_price(10.0)
    strat.on_price(11.0)
    assert strat.on_price(9.0) is Signal.SELL


def test_breakout_flat_inside_channel() -> None:
    strat = BreakoutStrategy(window=3)
    strat.on_price(10.0)
    strat.on_price(12.0)
    assert strat.on_price(11.0) is Signal.FLAT


def test_breakout_rejects_bad_window() -> None:
    with pytest.raises(ValueError, match="window"):
        BreakoutStrategy(window=1)


# --- Registry / factory ---------------------------------------------------


def test_registry_has_three_strategies() -> None:
    assert set(STRATEGIES) == {"momentum_ma", "mean_reversion", "breakout"}


@pytest.mark.parametrize("name", ["momentum_ma", "mean_reversion", "breakout"])
def test_build_strategy_dispatches(name: str) -> None:
    config = BotConfig(symbol="X", strategy=name, fast=2, slow=4)
    strat = build_strategy(config)
    assert isinstance(strat, Strategy)
    assert strat.name == name


def test_build_strategy_unknown_raises() -> None:
    config = BotConfig(symbol="X", strategy="does_not_exist")
    with pytest.raises(ValueError, match="unknown strategy"):
        build_strategy(config)
