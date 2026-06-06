"""Trading strategies and the strategy protocol.

A strategy is a pure ``price in -> signal out`` component: it buffers whatever
price history it needs and emits a directional
:class:`~automated_trading_bot.models.Signal`. Keeping strategies pure makes them
trivial to unit-test and lets the same object drive both the live runner and the
backtester.

This module ships three strategies:

* :class:`MomentumStrategy` — fast/slow simple-moving-average crossover.
* :class:`MeanReversionStrategy` — fade moves that stretch a configurable number
  of standard deviations away from a rolling mean (z-score band).
* :class:`BreakoutStrategy` — go long on a new rolling high, exit on a new
  rolling low (Donchian-style channel breakout).

All three implement the :class:`Strategy` protocol and can be created from a
:class:`~automated_trading_bot.config.BotConfig` via :func:`build_strategy`.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from automated_trading_bot.models import Signal

if TYPE_CHECKING:
    from automated_trading_bot.config import BotConfig


def simple_moving_average(prices: list[float], window: int) -> float:
    """Return the simple moving average of the last ``window`` prices.

    Args:
        prices: Price history, most recent last.
        window: Number of trailing prices to average; must be positive.

    Returns:
        The mean of the last ``window`` prices.

    Raises:
        ValueError: If ``window`` is not positive or exceeds the history length.
    """
    if window <= 0:
        msg = f"window must be positive, got {window}"
        raise ValueError(msg)
    if window > len(prices):
        msg = f"need at least {window} prices, got {len(prices)}"
        raise ValueError(msg)
    return sum(prices[-window:]) / window


def rolling_std(prices: list[float], window: int) -> float:
    """Return the population standard deviation of the last ``window`` prices.

    Args:
        prices: Price history, most recent last.
        window: Number of trailing prices to use; must be positive.

    Returns:
        The population standard deviation of the window (``0.0`` for a flat
        window).

    Raises:
        ValueError: If ``window`` is not positive or exceeds the history length.
    """
    if window <= 0:
        msg = f"window must be positive, got {window}"
        raise ValueError(msg)
    if window > len(prices):
        msg = f"need at least {window} prices, got {len(prices)}"
        raise ValueError(msg)
    sample = prices[-window:]
    mean = sum(sample) / window
    variance = sum((p - mean) ** 2 for p in sample) / window
    return float(variance**0.5)


@runtime_checkable
class Strategy(Protocol):
    """A pure price-to-signal strategy.

    Implementations buffer their own price history and return a fresh
    :class:`Signal` from :meth:`on_price`. They expose a stable ``name`` used in
    config, reports, and the CLI.
    """

    name: str

    def on_price(self, price: float) -> Signal:
        """Update internal state with ``price`` and return the new signal."""
        ...


class StrategyFactory(Protocol):
    """A strategy class buildable from a :class:`BotConfig`."""

    name: str

    def from_config(self, config: BotConfig) -> Strategy:
        """Construct a strategy instance from ``config``."""
        ...


class MomentumStrategy:
    """Fast/slow moving-average crossover momentum strategy.

    The strategy is stateful only in that it buffers the most recent prices it
    needs (``slow`` bars); it holds no position itself — sizing and execution are
    the runner's responsibility.
    """

    name = "momentum_ma"

    def __init__(self, fast: int, slow: int) -> None:
        """Create the strategy from fast and slow window lengths.

        Args:
            fast: Fast moving-average window.
            slow: Slow moving-average window; must exceed ``fast``.

        Raises:
            ValueError: If ``slow`` is not strictly greater than ``fast``.
        """
        if slow <= fast:
            msg = f"slow ({slow}) must be greater than fast ({fast})"
            raise ValueError(msg)
        self.fast = fast
        self.slow = slow
        self._prices: deque[float] = deque(maxlen=slow)

    @classmethod
    def from_config(cls, config: BotConfig) -> MomentumStrategy:
        """Build a strategy from a :class:`BotConfig`."""
        return cls(fast=config.fast, slow=config.slow)

    def on_price(self, price: float) -> Signal:
        """Update the rolling window with ``price`` and return the new signal.

        Returns ``Signal.FLAT`` until at least ``slow`` prices have been seen.
        """
        self._prices.append(price)
        if len(self._prices) < self.slow:
            return Signal.FLAT
        history = list(self._prices)
        fast_ma = simple_moving_average(history, self.fast)
        slow_ma = simple_moving_average(history, self.slow)
        if fast_ma > slow_ma:
            return Signal.BUY
        if fast_ma < slow_ma:
            return Signal.SELL
        return Signal.FLAT


class MeanReversionStrategy:
    """Z-score band mean-reversion strategy.

    Buys when price falls ``threshold`` standard deviations *below* the rolling
    mean (oversold) and sells when it rises ``threshold`` deviations *above*
    (overbought) — the opposite stance to momentum. Inside the band the signal is
    ``FLAT``.
    """

    name = "mean_reversion"

    def __init__(self, window: int, threshold: float = 1.0) -> None:
        """Create the strategy.

        Args:
            window: Lookback for the rolling mean and standard deviation; must be
                at least 2.
            threshold: Number of standard deviations from the mean that triggers
                a trade; must be positive.

        Raises:
            ValueError: If ``window`` < 2 or ``threshold`` <= 0.
        """
        if window < 2:
            msg = f"window must be >= 2, got {window}"
            raise ValueError(msg)
        if threshold <= 0.0:
            msg = f"threshold must be positive, got {threshold}"
            raise ValueError(msg)
        self.window = window
        self.threshold = threshold
        self._prices: deque[float] = deque(maxlen=window)

    @classmethod
    def from_config(cls, config: BotConfig) -> MeanReversionStrategy:
        """Build a strategy from a :class:`BotConfig` (uses ``slow`` as window)."""
        return cls(window=config.slow, threshold=config.threshold)

    def on_price(self, price: float) -> Signal:
        """Update the rolling window and return the mean-reversion signal."""
        self._prices.append(price)
        if len(self._prices) < self.window:
            return Signal.FLAT
        history = list(self._prices)
        mean = simple_moving_average(history, self.window)
        std = rolling_std(history, self.window)
        if std == 0.0:
            return Signal.FLAT
        z = (price - mean) / std
        if z <= -self.threshold:
            return Signal.BUY
        if z >= self.threshold:
            return Signal.SELL
        return Signal.FLAT


class BreakoutStrategy:
    """Donchian-channel breakout strategy.

    Goes long (``BUY``) when the latest price sets a new high over the lookback
    window and exits (``SELL``) when it sets a new low. Between extremes the
    signal is ``FLAT``, so an open long is held until a fresh low appears.
    """

    name = "breakout"

    def __init__(self, window: int) -> None:
        """Create the strategy.

        Args:
            window: Channel lookback (in bars); must be at least 2.

        Raises:
            ValueError: If ``window`` < 2.
        """
        if window < 2:
            msg = f"window must be >= 2, got {window}"
            raise ValueError(msg)
        self.window = window
        self._prices: deque[float] = deque(maxlen=window)

    @classmethod
    def from_config(cls, config: BotConfig) -> BreakoutStrategy:
        """Build a strategy from a :class:`BotConfig` (uses ``slow`` as window)."""
        return cls(window=config.slow)

    def on_price(self, price: float) -> Signal:
        """Update the channel and return the breakout signal.

        The current price is compared against the window *excluding* itself, so a
        new extreme is genuinely new. Returns ``FLAT`` until the window is full.
        """
        prior = list(self._prices)
        self._prices.append(price)
        if len(prior) < self.window - 1 or not prior:
            return Signal.FLAT
        if price > max(prior):
            return Signal.BUY
        if price < min(prior):
            return Signal.SELL
        return Signal.FLAT


#: Registry of strategy names to their classes, used by :func:`build_strategy`.
STRATEGIES: dict[str, StrategyFactory] = {
    MomentumStrategy.name: MomentumStrategy,
    MeanReversionStrategy.name: MeanReversionStrategy,
    BreakoutStrategy.name: BreakoutStrategy,
}


def build_strategy(config: BotConfig) -> Strategy:
    """Construct the strategy named by ``config.strategy``.

    Args:
        config: Bot configuration; ``config.strategy`` selects the implementation.

    Returns:
        A ready-to-use strategy implementing the :class:`Strategy` protocol.

    Raises:
        ValueError: If ``config.strategy`` is not a known strategy name.
    """
    try:
        factory = STRATEGIES[config.strategy]
    except KeyError:
        known = ", ".join(sorted(STRATEGIES))
        msg = f"unknown strategy {config.strategy!r}; choose one of: {known}"
        raise ValueError(msg) from None
    return factory.from_config(config)
