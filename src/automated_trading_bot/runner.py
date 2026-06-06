"""The bot runner: turn a stream of bars into paper trades.

On each bar the runner:

1. asks the strategy for a :class:`~automated_trading_bot.models.Signal`,
2. asks the :class:`~automated_trading_bot.risk.RiskManager` for a target size,
3. rebalances the paper position toward that target, recording any
   :class:`~automated_trading_bot.models.Fill`,
4. marks the account to market.

The account is long/flat (a ``SELL`` signal flattens an existing long). All
execution is simulated in memory, so the runner has no external dependencies and
runs fully offline.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import math

from automated_trading_bot.config import BotConfig
from automated_trading_bot.models import Fill, Order, Signal
from automated_trading_bot.risk import RiskManager
from automated_trading_bot.strategy import MomentumStrategy


class BotRunner:
    """Drives a strategy + risk manager over a price stream as paper trades."""

    def __init__(self, config: BotConfig) -> None:
        """Create a runner and its strategy/risk components from ``config``."""
        self.config = config
        self.strategy = MomentumStrategy.from_config(config)
        self.risk = RiskManager.from_config(config)
        self.cash: float = config.starting_equity
        self.position: float = 0.0
        self.fills: list[Fill] = []

    def equity(self, price: float) -> float:
        """Return mark-to-market equity at ``price`` (cash + position value)."""
        return self.cash + self.position * price

    def on_bar(self, price: float) -> Signal:
        """Process one bar: compute signal, size, and execute toward target.

        Args:
            price: The bar's price (used as the execution price).

        Returns:
            The signal produced by the strategy for this bar.
        """
        signal = self.strategy.on_price(price)
        equity = self.equity(price)
        target = self.risk.position_size(signal, equity, price)
        if signal is Signal.SELL:
            target = 0.0  # long/flat account: a sell flattens.

        delta = target - self.position
        if not math.isclose(delta, 0.0, abs_tol=1e-12):
            side = Signal.BUY if delta > 0 else Signal.SELL
            fee = abs(delta) * price * self.config.fee_rate
            self.cash -= delta * price + fee
            self.position = target
            self.fills.append(Fill(Order(self.config.symbol, side, abs(delta), price), fee=fee))
        return signal

    def run(self, prices: list[float]) -> float:
        """Run the bot over ``prices`` and return final mark-to-market equity."""
        last = self.config.starting_equity
        for price in prices:
            self.on_bar(price)
            last = self.equity(price)
        return last
