"""Tests for :mod:`automated_trading_bot.strategy`."""

from __future__ import annotations

import pytest

from automated_trading_bot.models import Signal
from automated_trading_bot.strategy import MomentumStrategy, simple_moving_average


def test_simple_moving_average_known_value() -> None:
    assert simple_moving_average([1.0, 2.0, 3.0, 4.0], window=2) == 3.5
    assert simple_moving_average([1.0, 2.0, 3.0, 4.0], window=4) == 2.5


def test_sma_rejects_bad_window() -> None:
    with pytest.raises(ValueError):
        simple_moving_average([1.0, 2.0], window=0)
    with pytest.raises(ValueError):
        simple_moving_average([1.0, 2.0], window=5)


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
