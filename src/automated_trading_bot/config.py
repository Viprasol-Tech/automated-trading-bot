"""Configuration model for the automated trading bot.

The bot is fully config-driven: a single :class:`BotConfig` describes the symbol
to trade, which strategy to run and its windows, the fraction of equity risked
per trade, and the risk guardrails (max concurrent positions and a daily-loss
limit). Validation lives here so an invalid bot can never start.

Configs are JSON-serialisable *profiles*: use :meth:`BotConfig.from_json_file`
and :meth:`BotConfig.to_json_file` to round-trip a profile to disk.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BotConfig(BaseModel):
    """Validated configuration for a single automated trading bot.

    Attributes:
        symbol: The instrument to trade, e.g. ``"BTC/USDT"``.
        strategy: Strategy name (``momentum_ma``, ``mean_reversion`` or
            ``breakout``).
        fast: Window (in bars) of the fast moving average (momentum only).
        slow: Window (in bars) of the slow moving average / strategy lookback;
            must exceed ``fast``.
        threshold: Z-score band for the mean-reversion strategy.
        risk_fraction: Fraction of equity to risk per position, in ``(0, 1]``.
        max_positions: Maximum number of concurrent open positions allowed.
        daily_loss_limit: Fraction of *starting* equity that may be lost in a day
            before trading halts, in ``(0, 1]``. ``1.0`` effectively disables it.
        starting_equity: Initial account equity used by the runner and backtest.
        fee_rate: Per-trade proportional fee, e.g. ``0.001`` for 10 bps.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    strategy: str = Field(default="momentum_ma", min_length=1)
    fast: int = Field(default=10, ge=1)
    slow: int = Field(default=30, ge=2)
    threshold: float = Field(default=1.0, gt=0.0)
    risk_fraction: float = Field(default=0.1, gt=0.0, le=1.0)
    max_positions: int = Field(default=1, ge=1)
    daily_loss_limit: float = Field(default=1.0, gt=0.0, le=1.0)
    starting_equity: float = Field(default=10_000.0, gt=0.0)
    fee_rate: float = Field(default=0.0, ge=0.0, lt=1.0)

    @model_validator(mode="after")
    def _check_windows(self) -> BotConfig:
        """Ensure the slow window is strictly longer than the fast window."""
        if self.slow <= self.fast:
            msg = f"slow ({self.slow}) must be greater than fast ({self.fast})"
            raise ValueError(msg)
        return self

    @classmethod
    def from_json(cls, data: str) -> BotConfig:
        """Parse a :class:`BotConfig` from a JSON string."""
        return cls.model_validate(json.loads(data))

    @classmethod
    def from_json_file(cls, path: str | Path) -> BotConfig:
        """Load a config profile from a JSON file on disk.

        Args:
            path: Path to a JSON profile.

        Returns:
            The validated configuration.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            ValidationError: If the file contents are not a valid config.
        """
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    def to_json(self, *, indent: int = 2) -> str:
        """Serialise the config to a pretty JSON string."""
        return json.dumps(self.model_dump(), indent=indent, sort_keys=True)

    def to_json_file(self, path: str | Path, *, indent: int = 2) -> None:
        """Write the config to ``path`` as a JSON profile."""
        Path(path).write_text(self.to_json(indent=indent) + "\n", encoding="utf-8")
