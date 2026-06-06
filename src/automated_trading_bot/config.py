"""Configuration model for the automated trading bot.

The bot is fully config-driven: a single :class:`BotConfig` describes the symbol
to trade, the moving-average windows for the strategy, and the fraction of equity
risked per trade. Validation lives here so an invalid bot can never start.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BotConfig(BaseModel):
    """Validated configuration for a single automated trading bot.

    Attributes:
        symbol: The instrument to trade, e.g. ``"BTC/USDT"``.
        fast: Window (in bars) of the fast moving average.
        slow: Window (in bars) of the slow moving average; must exceed ``fast``.
        risk_fraction: Fraction of equity to risk per position, in ``(0, 1]``.
        starting_equity: Initial account equity used by the runner and backtest.
        fee_rate: Per-trade proportional fee, e.g. ``0.001`` for 10 bps.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    fast: int = Field(default=10, ge=1)
    slow: int = Field(default=30, ge=2)
    risk_fraction: float = Field(default=0.1, gt=0.0, le=1.0)
    starting_equity: float = Field(default=10_000.0, gt=0.0)
    fee_rate: float = Field(default=0.0, ge=0.0, lt=1.0)

    @model_validator(mode="after")
    def _check_windows(self) -> BotConfig:
        """Ensure the slow window is strictly longer than the fast window."""
        if self.slow <= self.fast:
            msg = f"slow ({self.slow}) must be greater than fast ({self.fast})"
            raise ValueError(msg)
        return self
