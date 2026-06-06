"""Position sizing and risk management.

The risk layer converts a directional signal and the current account equity into
a concrete order quantity, never allocating more than ``risk_fraction`` of equity
to a single position. This is the one place capital exposure is decided, so it is
small, pure, and heavily tested.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from automated_trading_bot.config import BotConfig
from automated_trading_bot.models import Signal


class RiskManager:
    """Caps per-position notional at a fraction of current equity."""

    def __init__(self, risk_fraction: float) -> None:
        """Create a risk manager.

        Args:
            risk_fraction: Maximum fraction of equity to deploy per position,
                in ``(0, 1]``.

        Raises:
            ValueError: If ``risk_fraction`` is outside ``(0, 1]``.
        """
        if not 0.0 < risk_fraction <= 1.0:
            msg = f"risk_fraction must be in (0, 1], got {risk_fraction}"
            raise ValueError(msg)
        self.risk_fraction = risk_fraction

    @classmethod
    def from_config(cls, config: BotConfig) -> RiskManager:
        """Build a risk manager from a :class:`BotConfig`."""
        return cls(risk_fraction=config.risk_fraction)

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
