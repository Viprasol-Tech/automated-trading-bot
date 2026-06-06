"""Tests for :mod:`automated_trading_bot.config`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from automated_trading_bot.config import BotConfig


def test_valid_config_defaults() -> None:
    config = BotConfig(symbol="BTC/USDT")
    assert config.fast == 10
    assert config.slow == 30
    assert config.risk_fraction == 0.1
    assert config.starting_equity == 10_000.0


def test_slow_must_exceed_fast() -> None:
    with pytest.raises(ValidationError, match="slow"):
        BotConfig(symbol="X", fast=30, slow=10)


def test_risk_fraction_must_be_in_unit_interval() -> None:
    with pytest.raises(ValidationError):
        BotConfig(symbol="X", risk_fraction=0.0)
    with pytest.raises(ValidationError):
        BotConfig(symbol="X", risk_fraction=1.5)


def test_empty_symbol_rejected() -> None:
    with pytest.raises(ValidationError):
        BotConfig(symbol="")


def test_config_is_frozen_and_strict() -> None:
    config = BotConfig(symbol="X")
    with pytest.raises(ValidationError):
        config.symbol = "Y"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        BotConfig(symbol="X", unknown=1)  # type: ignore[call-arg]
