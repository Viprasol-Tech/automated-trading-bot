"""Tests for :mod:`automated_trading_bot.risk`."""

from __future__ import annotations

import pytest

from automated_trading_bot.config import BotConfig
from automated_trading_bot.models import Signal
from automated_trading_bot.risk import RiskManager


def test_position_size_capped_at_risk_fraction() -> None:
    risk = RiskManager(risk_fraction=0.25)
    # 25% of 10_000 = 2_500 notional; at price 50 -> 50 units.
    assert risk.position_size(Signal.BUY, equity=10_000.0, price=50.0) == 50.0


def test_notional_never_exceeds_budget() -> None:
    risk = RiskManager(risk_fraction=0.1)
    qty = risk.position_size(Signal.BUY, equity=10_000.0, price=123.45)
    notional = qty * 123.45
    assert notional == pytest.approx(1_000.0)
    assert notional <= 0.1 * 10_000.0 + 1e-9


def test_flat_signal_yields_zero() -> None:
    risk = RiskManager(risk_fraction=0.5)
    assert risk.position_size(Signal.FLAT, equity=10_000.0, price=10.0) == 0.0


def test_non_positive_inputs_yield_zero() -> None:
    risk = RiskManager(risk_fraction=0.5)
    assert risk.position_size(Signal.BUY, equity=0.0, price=10.0) == 0.0
    assert risk.position_size(Signal.BUY, equity=10_000.0, price=0.0) == 0.0


def test_invalid_risk_fraction_rejected() -> None:
    with pytest.raises(ValueError, match="risk_fraction"):
        RiskManager(risk_fraction=0.0)
    with pytest.raises(ValueError, match="risk_fraction"):
        RiskManager(risk_fraction=1.5)


# --- Concurrency cap ------------------------------------------------------


def test_can_open_respects_max_positions() -> None:
    risk = RiskManager(risk_fraction=0.5, max_positions=2)
    assert risk.can_open(0) is True
    assert risk.can_open(1) is True
    assert risk.can_open(2) is False
    assert risk.can_open(3) is False


def test_invalid_max_positions_rejected() -> None:
    with pytest.raises(ValueError, match="max_positions"):
        RiskManager(risk_fraction=0.5, max_positions=0)


# --- Daily-loss limit -----------------------------------------------------


def test_not_halted_when_within_limit() -> None:
    risk = RiskManager(risk_fraction=0.5, daily_loss_limit=0.1)
    # 5% loss is within a 10% limit.
    assert risk.is_halted(day_start_equity=10_000.0, current_equity=9_500.0) is False


def test_halted_when_limit_breached() -> None:
    risk = RiskManager(risk_fraction=0.5, daily_loss_limit=0.1)
    # 10% loss reaches the limit.
    assert risk.is_halted(day_start_equity=10_000.0, current_equity=9_000.0) is True
    # 15% loss exceeds it.
    assert risk.is_halted(day_start_equity=10_000.0, current_equity=8_500.0) is True


def test_profit_never_halts() -> None:
    risk = RiskManager(risk_fraction=0.5, daily_loss_limit=0.01)
    assert risk.is_halted(day_start_equity=10_000.0, current_equity=12_000.0) is False


def test_non_positive_day_start_halts() -> None:
    risk = RiskManager(risk_fraction=0.5, daily_loss_limit=0.5)
    assert risk.is_halted(day_start_equity=0.0, current_equity=0.0) is True


def test_invalid_daily_loss_limit_rejected() -> None:
    with pytest.raises(ValueError, match="daily_loss_limit"):
        RiskManager(risk_fraction=0.5, daily_loss_limit=0.0)
    with pytest.raises(ValueError, match="daily_loss_limit"):
        RiskManager(risk_fraction=0.5, daily_loss_limit=1.5)


def test_from_config_carries_all_guardrails() -> None:
    config = BotConfig(symbol="X", risk_fraction=0.3, max_positions=4, daily_loss_limit=0.2)
    risk = RiskManager.from_config(config)
    assert risk.risk_fraction == 0.3
    assert risk.max_positions == 4
    assert risk.daily_loss_limit == 0.2
