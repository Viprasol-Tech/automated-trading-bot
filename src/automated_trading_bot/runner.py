"""The bot runner: turn a stream of bars into paper trades.

On each bar the runner:

1. asks the strategy for a :class:`~automated_trading_bot.models.Signal`,
2. checks the :class:`~automated_trading_bot.risk.RiskManager` guardrails
   (daily-loss halt and position-concurrency cap),
3. asks the risk manager for a target size,
4. rebalances the paper position toward that target, recording any
   :class:`~automated_trading_bot.models.Fill`,
5. marks the account to market.

The account is long/flat (a ``SELL`` signal flattens an existing long). Once the
daily-loss limit is hit the runner stops opening or growing positions for the
rest of the run (it still allows exits). All execution is simulated in memory, so
the runner has no external dependencies and runs fully offline.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import math

from automated_trading_bot.config import BotConfig
from automated_trading_bot.models import Fill, Order, Signal
from automated_trading_bot.risk import RiskManager
from automated_trading_bot.strategy import build_strategy


class BotRunner:
    """Drives a strategy + risk manager over a price stream as paper trades."""

    def __init__(self, config: BotConfig) -> None:
        """Create a runner and its strategy/risk components from ``config``."""
        self.config = config
        self.strategy = build_strategy(config)
        self.risk = RiskManager.from_config(config)
        self.cash: float = config.starting_equity
        self.position: float = 0.0
        self.fills: list[Fill] = []
        self._day_start_equity: float = config.starting_equity
        self.halted: bool = False

    def equity(self, price: float) -> float:
        """Return mark-to-market equity at ``price`` (cash + position value)."""
        return self.cash + self.position * price

    @property
    def open_positions(self) -> int:
        """Number of currently open positions (0 or 1 in this long/flat model)."""
        return 1 if not math.isclose(self.position, 0.0, abs_tol=1e-12) else 0

    def on_bar(self, price: float) -> Signal:
        """Process one bar: compute signal, size, and execute toward target.

        Honors the risk guardrails: if the daily-loss limit is breached the
        position is flattened and no new exposure is taken; if the concurrency
        cap is reached a new position is not opened.

        Args:
            price: The bar's price (used as the execution price).

        Returns:
            The signal produced by the strategy for this bar.
        """
        signal = self.strategy.on_price(price)
        equity = self.equity(price)

        if self.risk.is_halted(self._day_start_equity, equity):
            self.halted = True

        target = self.risk.position_size(signal, equity, price)
        if signal is Signal.SELL or self.halted:
            target = 0.0  # long/flat account: a sell (or halt) flattens.

        # Concurrency cap: do not *open* a fresh position past the limit.
        opening = self.open_positions == 0 and target > 0.0
        if opening and not self.risk.can_open(self.open_positions):
            target = 0.0

        delta = target - self.position
        if not math.isclose(delta, 0.0, abs_tol=1e-12):
            side = Signal.BUY if delta > 0 else Signal.SELL
            fee = abs(delta) * price * self.config.fee_rate
            self.cash -= delta * price + fee
            self.position = target
            self.fills.append(Fill(Order(self.config.symbol, side, abs(delta), price), fee=fee))
        return signal

    def start_new_day(self, price: float) -> None:
        """Reset the daily-loss baseline and clear the halt flag.

        Call this at a session boundary so the daily-loss limit measures losses
        relative to the *current* equity rather than the original starting
        equity.

        Args:
            price: Current price, used to mark equity for the new baseline.
        """
        self._day_start_equity = self.equity(price)
        self.halted = False

    def run(self, prices: list[float]) -> float:
        """Run the bot over ``prices`` and return final mark-to-market equity."""
        last = self.config.starting_equity
        for price in prices:
            self.on_bar(price)
            last = self.equity(price)
        return last
