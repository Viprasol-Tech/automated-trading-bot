"""A small scheduler abstraction for driving the bot at a fixed cadence.

Live trading polls the market on a clock; the rest of the codebase is pure and
synchronous. This module bridges the two with a tiny, dependency-free scheduler
that repeatedly invokes a callback and is fully deterministic in tests.

* :class:`Scheduler` — the protocol every scheduler satisfies.
* :class:`IntervalScheduler` — real wall-clock scheduler (uses ``time.sleep``).
* :class:`ManualScheduler` — a test/replay scheduler whose clock you advance by
  hand, so scheduled behaviour can be unit-tested without sleeping.

Both schedulers run for a bounded number of ticks and stop early if the callback
returns ``False``, which the runner uses to honor a daily-loss halt.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol, runtime_checkable

#: A tick callback: receives the (zero-based) tick index and returns whether to
#: continue scheduling. Returning ``False`` stops the loop.
TickCallback = Callable[[int], bool]


@runtime_checkable
class Scheduler(Protocol):
    """Drives a callback for up to ``max_ticks`` ticks."""

    def run(self, callback: TickCallback, max_ticks: int) -> int:
        """Invoke ``callback`` until it returns ``False`` or ``max_ticks`` is hit.

        Returns the number of ticks actually executed.
        """
        ...


class IntervalScheduler:
    """Wall-clock scheduler that ticks every ``interval`` seconds."""

    def __init__(self, interval: float, *, sleep: Callable[[float], None] = time.sleep) -> None:
        """Create the scheduler.

        Args:
            interval: Seconds between ticks; must be non-negative.
            sleep: Sleep function, injectable for testing (defaults to
                :func:`time.sleep`).

        Raises:
            ValueError: If ``interval`` is negative.
        """
        if interval < 0.0:
            msg = f"interval must be non-negative, got {interval}"
            raise ValueError(msg)
        self.interval = interval
        self._sleep = sleep

    def run(self, callback: TickCallback, max_ticks: int) -> int:
        """Run the callback every ``interval`` seconds for up to ``max_ticks``."""
        executed = 0
        for tick in range(max_ticks):
            if tick > 0:
                self._sleep(self.interval)
            executed += 1
            if not callback(tick):
                break
        return executed


class ManualScheduler:
    """Deterministic scheduler with no sleeping, for tests and replays."""

    def __init__(self) -> None:
        """Create a manual scheduler that records how many ticks it ran."""
        self.ticks_run = 0

    def run(self, callback: TickCallback, max_ticks: int) -> int:
        """Invoke ``callback`` immediately for up to ``max_ticks`` ticks."""
        self.ticks_run = 0
        for tick in range(max_ticks):
            self.ticks_run += 1
            if not callback(tick):
                break
        return self.ticks_run
