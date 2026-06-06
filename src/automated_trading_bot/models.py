"""Core value types for the automated trading bot.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Signal(int, Enum):
    """A directional trading signal produced by a strategy."""

    SELL = -1
    FLAT = 0
    BUY = 1


@dataclass(slots=True, frozen=True)
class Order:
    """A paper order to be applied to the account by the runner."""

    symbol: str
    signal: Signal
    quantity: float
    price: float


@dataclass(slots=True, frozen=True)
class Fill:
    """A filled order, with the fee charged on execution."""

    order: Order
    fee: float = 0.0
