"""Moving-average momentum strategy.

The strategy maintains a rolling price window and emits a directional
:class:`~automated_trading_bot.models.Signal` from the crossover of a fast and a
slow simple moving average:

* fast SMA above slow SMA -> ``BUY`` (uptrend / momentum long)
* fast SMA below slow SMA -> ``SELL`` (downtrend)
* not enough history, or equal averages -> ``FLAT``

Keeping the strategy pure (``price in -> signal out``) makes it trivial to
unit-test and to drive from both the live runner and the backtester.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from collections import deque

from automated_trading_bot.config import BotConfig
from automated_trading_bot.models import Signal


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
