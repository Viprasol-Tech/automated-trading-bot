"""Backtesting: run a bot over a price series and summarise performance.

Reuses :class:`~automated_trading_bot.runner.BotRunner` so the backtest executes
exactly the same signal -> guardrails -> size -> order pipeline as a live run.
Per-bar equity is recorded and reduced to a set of standard performance metrics:
total return, max drawdown, annualised Sharpe ratio, volatility, win rate and a
human-readable report via :meth:`BacktestResult.report`.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from automated_trading_bot.config import BotConfig
from automated_trading_bot.runner import BotRunner

#: Trading periods per year used to annualise Sharpe and volatility.
PERIODS_PER_YEAR = 252


@dataclass(slots=True, frozen=True)
class BacktestResult:
    """Summary statistics for a completed backtest.

    Attributes:
        starting_equity: Equity before the first bar.
        final_equity: Mark-to-market equity after the last bar.
        total_return: ``final / starting - 1``.
        max_drawdown: Worst peak-to-trough decline of the equity curve, as a
            non-negative fraction (``0.2`` == a 20% drawdown).
        sharpe: Annualised Sharpe ratio of per-bar returns (0.0 if undefined).
        volatility: Annualised standard deviation of per-bar returns.
        win_rate: Fraction of bars with a positive return, in ``[0, 1]``.
        num_trades: Number of fills executed.
        equity_curve: Mark-to-market equity after each bar.
    """

    starting_equity: float
    final_equity: float
    total_return: float
    max_drawdown: float
    sharpe: float
    volatility: float
    win_rate: float
    num_trades: int
    equity_curve: list[float]

    def report(self) -> str:
        """Return a multi-line, human-readable performance report."""
        lines = [
            "Backtest report",
            "===============",
            f"Starting equity : {self.starting_equity:,.2f}",
            f"Final equity    : {self.final_equity:,.2f}",
            f"Total return    : {self.total_return:+.2%}",
            f"Max drawdown    : {self.max_drawdown:.2%}",
            f"Sharpe (ann.)   : {self.sharpe:.2f}",
            f"Volatility (ann): {self.volatility:.2%}",
            f"Win rate        : {self.win_rate:.2%}",
            f"Trades          : {self.num_trades}",
        ]
        return "\n".join(lines)


def _max_drawdown(curve: list[float]) -> float:
    """Return the maximum peak-to-trough drawdown of ``curve`` as a fraction."""
    peak = float("-inf")
    worst = 0.0
    for value in curve:
        peak = max(peak, value)
        if peak > 0.0:
            worst = max(worst, (peak - value) / peak)
    return worst


def _period_returns(curve: list[float]) -> list[float]:
    """Return simple per-bar returns from an equity curve."""
    returns: list[float] = []
    for prev, cur in pairwise(curve):
        if prev != 0.0:
            returns.append(cur / prev - 1.0)
    return returns


def _sharpe(returns: list[float]) -> float:
    """Return the annualised Sharpe ratio of ``returns`` (0.0 if undefined)."""
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = variance**0.5
    if std == 0.0:
        return 0.0
    return float((mean / std) * (PERIODS_PER_YEAR**0.5))


def _volatility(returns: list[float]) -> float:
    """Return the annualised standard deviation of ``returns``."""
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return float((variance**0.5) * (PERIODS_PER_YEAR**0.5))


def _win_rate(returns: list[float]) -> float:
    """Return the fraction of strictly-positive returns."""
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r > 0.0)
    return wins / len(returns)


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
    returns = _period_returns(curve)
    return BacktestResult(
        starting_equity=start,
        final_equity=final,
        total_return=final / start - 1.0,
        max_drawdown=_max_drawdown(curve),
        sharpe=_sharpe(returns),
        volatility=_volatility(returns),
        win_rate=_win_rate(returns),
        num_trades=len(runner.fills),
        equity_curve=curve,
    )
