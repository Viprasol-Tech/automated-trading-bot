"""Backtesting: run a bot over a price series and summarise performance.

Reuses :class:`~automated_trading_bot.runner.BotRunner` so the backtest executes
exactly the same signal -> size -> order pipeline as a live run. Per-bar equity is
recorded and reduced to a small set of standard metrics.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass

from automated_trading_bot.config import BotConfig
from automated_trading_bot.runner import BotRunner


@dataclass(slots=True, frozen=True)
class BacktestResult:
    """Summary statistics for a completed backtest.

    Attributes:
        starting_equity: Equity before the first bar.
        final_equity: Mark-to-market equity after the last bar.
        total_return: ``final / starting - 1``.
        max_drawdown: Worst peak-to-trough decline of the equity curve, as a
            non-negative fraction (``0.2`` == a 20% drawdown).
        num_trades: Number of fills executed.
        equity_curve: Mark-to-market equity after each bar.
    """

    starting_equity: float
    final_equity: float
    total_return: float
    max_drawdown: float
    num_trades: int
    equity_curve: list[float]


def _max_drawdown(curve: list[float]) -> float:
    """Return the maximum peak-to-trough drawdown of ``curve`` as a fraction."""
    peak = float("-inf")
    worst = 0.0
    for value in curve:
        peak = max(peak, value)
        if peak > 0.0:
            worst = max(worst, (peak - value) / peak)
    return worst


def run_backtest(config: BotConfig, prices: list[float]) -> BacktestResult:
    """Run a full backtest of ``config`` over ``prices``.

    Args:
        config: The bot configuration to evaluate.
        prices: Ordered price series (oldest first).

    Returns:
        A :class:`BacktestResult` summarising the run.

    Raises:
        ValueError: If ``prices`` is empty.
    """
    if not prices:
        msg = "prices must not be empty"
        raise ValueError(msg)

    runner = BotRunner(config)
    curve: list[float] = []
    for price in prices:
        runner.on_bar(price)
        curve.append(runner.equity(price))

    final = curve[-1]
    start = config.starting_equity
    return BacktestResult(
        starting_equity=start,
        final_equity=final,
        total_return=final / start - 1.0,
        max_drawdown=_max_drawdown(curve),
        num_trades=len(runner.fills),
        equity_curve=curve,
    )
