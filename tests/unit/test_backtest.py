"""Tests for :mod:`automated_trading_bot.backtest` and the runner."""

from __future__ import annotations

import math

import pytest

from automated_trading_bot.backtest import run_backtest
from automated_trading_bot.config import BotConfig
from automated_trading_bot.runner import BotRunner


def _trend(n: int = 120) -> list[float]:
    return [100.0 + i for i in range(n)]


def test_backtest_runs_and_reports_curve() -> None:
    config = BotConfig(symbol="X", fast=3, slow=8, risk_fraction=0.5)
    result = run_backtest(config, _trend())
    assert len(result.equity_curve) == len(_trend())
    assert result.starting_equity == config.starting_equity
    assert result.num_trades >= 1
    # Profitable on a clean uptrend.
    assert result.final_equity > result.starting_equity
    assert result.total_return == pytest.approx(result.final_equity / result.starting_equity - 1.0)


def test_backtest_rejects_empty_prices() -> None:
    config = BotConfig(symbol="X")
    with pytest.raises(ValueError, match="empty"):
        run_backtest(config, [])


def test_runner_position_respects_risk_cap() -> None:
    config = BotConfig(symbol="X", fast=2, slow=4, risk_fraction=0.2)
    runner = BotRunner(config)
    for price in [1.0, 2.0, 3.0, 4.0, 5.0]:
        runner.on_bar(price)
    # After a buy at price 5, notional held <= 20% of equity at that bar.
    equity = runner.equity(5.0)
    notional = runner.position * 5.0
    assert notional <= 0.2 * equity + 1e-6


def test_runner_flat_market_makes_no_trades() -> None:
    config = BotConfig(symbol="X", fast=2, slow=4)
    runner = BotRunner(config)
    final = runner.run([100.0] * 50)
    assert runner.fills == []
    assert math.isclose(final, config.starting_equity)
