"""Tests for :mod:`automated_trading_bot.backtest` and the runner."""

from __future__ import annotations

import math

import pytest

from automated_trading_bot.backtest import (
    BacktestResult,
    _max_drawdown,
    _sharpe,
    _win_rate,
    run_backtest,
)
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


def test_backtest_reports_metrics() -> None:
    config = BotConfig(symbol="X", fast=3, slow=8, risk_fraction=0.5)
    result = run_backtest(config, _trend())
    assert isinstance(result, BacktestResult)
    assert 0.0 <= result.win_rate <= 1.0
    assert result.volatility >= 0.0
    # A clean uptrend with a long bias should have a positive Sharpe.
    assert result.sharpe > 0.0


def test_report_is_multiline_and_mentions_metrics() -> None:
    config = BotConfig(symbol="X", fast=3, slow=8, risk_fraction=0.5)
    text = run_backtest(config, _trend()).report()
    assert "Sharpe" in text
    assert "Win rate" in text
    assert text.count("\n") >= 8


def test_backtest_rejects_empty_prices() -> None:
    config = BotConfig(symbol="X")
    with pytest.raises(ValueError, match="empty"):
        run_backtest(config, [])


def test_max_drawdown_known_curve() -> None:
    # Peak 100 -> trough 80 is a 20% drawdown.
    assert _max_drawdown([100.0, 90.0, 80.0, 120.0]) == pytest.approx(0.2)


def test_sharpe_zero_for_constant_returns() -> None:
    assert _sharpe([0.01, 0.01, 0.01]) == 0.0


def test_win_rate_counts_positive_returns() -> None:
    assert _win_rate([0.1, -0.1, 0.2, 0.0]) == pytest.approx(0.5)
    assert _win_rate([]) == 0.0


# --- Runner ----------------------------------------------------------------


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


def test_runner_open_positions_property() -> None:
    config = BotConfig(symbol="X", fast=2, slow=4, risk_fraction=0.5)
    runner = BotRunner(config)
    assert runner.open_positions == 0
    for price in [1.0, 2.0, 3.0, 4.0, 5.0]:
        runner.on_bar(price)
    assert runner.open_positions == 1


def test_daily_loss_halt_flattens_and_blocks() -> None:
    # Tight 1% daily-loss limit; a down market after a long entry should halt.
    config = BotConfig(
        symbol="X", fast=2, slow=4, risk_fraction=1.0, daily_loss_limit=0.01, fee_rate=0.01
    )
    runner = BotRunner(config)
    # Rise to trigger a long, then crash.
    for price in [1.0, 2.0, 3.0, 4.0, 5.0]:
        runner.on_bar(price)
    assert runner.open_positions == 1
    for price in [4.0, 3.0, 2.0, 1.0]:
        runner.on_bar(price)
    assert runner.halted is True
    assert runner.open_positions == 0  # halt flattens the book


def test_start_new_day_resets_halt() -> None:
    config = BotConfig(symbol="X", fast=2, slow=4, daily_loss_limit=0.01)
    runner = BotRunner(config)
    runner.halted = True
    runner.start_new_day(price=100.0)
    assert runner.halted is False


def test_max_positions_one_blocks_second_concurrent_open() -> None:
    # With a long/flat model and max_positions=1, the book never exceeds one.
    config = BotConfig(symbol="X", fast=2, slow=4, risk_fraction=0.5, max_positions=1)
    runner = BotRunner(config)
    runner.run(_trend(40))
    assert runner.open_positions <= 1
