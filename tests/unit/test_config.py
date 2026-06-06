"""Tests for :mod:`automated_trading_bot.config`."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from automated_trading_bot.config import BotConfig


def test_valid_config_defaults() -> None:
    config = BotConfig(symbol="BTC/USDT")
    assert config.strategy == "momentum_ma"
    assert config.fast == 10
    assert config.slow == 30
    assert config.threshold == 1.0
    assert config.risk_fraction == 0.1
    assert config.max_positions == 1
    assert config.daily_loss_limit == 1.0
    assert config.starting_equity == 10_000.0


def test_slow_must_exceed_fast() -> None:
    with pytest.raises(ValidationError, match="slow"):
        BotConfig(symbol="X", fast=30, slow=10)


def test_risk_fraction_must_be_in_unit_interval() -> None:
    with pytest.raises(ValidationError):
        BotConfig(symbol="X", risk_fraction=0.0)
    with pytest.raises(ValidationError):
        BotConfig(symbol="X", risk_fraction=1.5)


def test_max_positions_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        BotConfig(symbol="X", max_positions=0)


def test_daily_loss_limit_bounds() -> None:
    with pytest.raises(ValidationError):
        BotConfig(symbol="X", daily_loss_limit=0.0)
    with pytest.raises(ValidationError):
        BotConfig(symbol="X", daily_loss_limit=1.5)


def test_empty_symbol_rejected() -> None:
    with pytest.raises(ValidationError):
        BotConfig(symbol="")


def test_config_is_frozen_and_strict() -> None:
    config = BotConfig(symbol="X")
    with pytest.raises(ValidationError):
        config.symbol = "Y"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        BotConfig(symbol="X", unknown=1)  # type: ignore[call-arg]


# --- JSON profile round-trip ----------------------------------------------


def test_json_round_trip_string() -> None:
    config = BotConfig(symbol="ETH/USDT", strategy="breakout", max_positions=3)
    restored = BotConfig.from_json(config.to_json())
    assert restored == config


def test_json_file_round_trip(tmp_path: Path) -> None:
    config = BotConfig(
        symbol="SOL/USDT",
        strategy="mean_reversion",
        threshold=1.5,
        daily_loss_limit=0.25,
    )
    path = tmp_path / "profile.json"
    config.to_json_file(path)
    assert path.exists()
    restored = BotConfig.from_json_file(path)
    assert restored == config


def test_from_json_file_validates(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"symbol": "X", "fast": 30, "slow": 10}', encoding="utf-8")
    with pytest.raises(ValidationError, match="slow"):
        BotConfig.from_json_file(path)


def test_from_json_file_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        BotConfig.from_json_file(tmp_path / "nope.json")
