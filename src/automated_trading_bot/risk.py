"""Position sizing and risk management.

The risk layer is the one place capital exposure is decided, so it is small,
pure, and heavily tested. It does three jobs:

1. **Position sizing** — never allocate more than ``risk_fraction`` of equity to
   a single position (:meth:`RiskManager.position_size`).
2. **Concurrency cap** — refuse to *open* a new position once ``max_positions``
   are already open (:meth:`RiskManager.can_open`).
3. **Daily-loss limit** — halt trading for the day once realised + unrealised
   losses breach ``daily_loss_limit`` of the day's starting equity
   (:meth:`RiskManager.is_halted`).

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from automated_trading_bot.config import BotConfig
from automated_trading_bot.models import Signal


class RiskManager:
    """Sizes positions and enforces concurrency and daily-loss guardrails."""

    def __init__(
        self,
        risk_fraction: float,
        max_positions: int = 1,
        daily_loss_limit: float = 1.0,
    ) -> None:
        """Create a risk manager.

        Args:
            risk_fraction: Maximum fraction of equity to deploy per position,
                in ``(0, 1]``.
            max_positions: Maximum number of concurrent open positions; >= 1.
            daily_loss_limit: Fraction of the day's starting equity that may be
                lost before trading halts, in ``(0, 1]``.

        Raises:
            ValueError: If any argument is outside its valid range.
        """
        if not 0.0 < risk_fraction <= 1.0:
            msg = f"risk_fraction must be in (0, 1], got {risk_fraction}"
            raise ValueError(msg)
        if max_positions < 1:
            msg = f"max_positions must be >= 1, got {max_positions}"
            raise ValueError(msg)
        if not 0.0 < daily_loss_limit <= 1.0:
            msg = f"daily_loss_limit must be in (0, 1], got {daily_loss_limit}"
            raise ValueError(msg)
        self.risk_fraction = risk_fraction
        self.max_positions = max_positions
        self.daily_loss_limit = daily_loss_limit

    @classmethod
    def from_config(cls, config: BotConfig) -> RiskManager:
        """Build a risk manager from a :class:`BotConfig`."""
        return cls(
            risk_fraction=config.risk_fraction,
            max_positions=config.max_positions,
            daily_loss_limit=config.daily_loss_limit,
        )

    def position_size(self, signal: Signal, equity: float, price: float) -> float:
        """Return the quantity to hold for ``signal`` given ``equity``.

        The notional deployed is capped at ``risk_fraction * equity``; the
        returned quantity is that capped notional divided by ``price``. A
        ``FLAT`` signal (or non-positive equity/price) yields a zero position.

        Args:
            signal: Desired direction.
            equity: Current account equity (quote currency).
            price: Current instrument price.

        Returns:
            The (non-negative) quantity to hold. Direction is conveyed by the
            signal, not the sign of this number.
        """
        if signal is Signal.FLAT or equity <= 0.0 or price <= 0.0:
            return 0.0
        budget = self.risk_fraction * equity
        return budget / price

    def can_open(self, open_positions: int) -> bool:
        """Return whether a new position may be opened.

        Args:
            open_positions: Number of positions currently open.

        Returns:
            ``True`` while fewer than ``max_positions`` are open.
        """
        return open_positions < self.max_positions

    def is_halted(self, day_start_equity: float, current_equity: float) -> bool:
        """Return whether the daily-loss limit has been breached.

        Args:
            day_start_equity: Equity at the start of the trading day.
            current_equity: Current mark-to-market equity.

        Returns:
            ``True`` once the loss from ``day_start_equity`` reaches the limit.
        """
        if day_start_equity <= 0.0:
            return True
        loss = (day_start_equity - current_equity) / day_start_equity
        return loss >= self.daily_loss_limit
