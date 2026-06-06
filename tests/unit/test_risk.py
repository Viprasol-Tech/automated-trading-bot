"""Tests for :mod:`automated_trading_bot.risk`."""

from __future__ import annotations

import pytest

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
