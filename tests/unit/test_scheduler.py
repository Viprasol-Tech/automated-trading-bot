"""Tests for :mod:`automated_trading_bot.scheduler`."""

from __future__ import annotations

import pytest

from automated_trading_bot.scheduler import (
    IntervalScheduler,
    ManualScheduler,
    Scheduler,
)


def test_manual_scheduler_runs_all_ticks() -> None:
    sched = ManualScheduler()
    seen: list[int] = []
    executed = sched.run(lambda i: seen.append(i) or True, max_ticks=5)
    assert executed == 5
    assert seen == [0, 1, 2, 3, 4]
    assert sched.ticks_run == 5


def test_manual_scheduler_stops_on_false() -> None:
    sched = ManualScheduler()
    executed = sched.run(lambda i: i < 2, max_ticks=10)
    assert executed == 3  # ticks 0, 1 returned True; tick 2 returned False


def test_manual_scheduler_satisfies_protocol() -> None:
    assert isinstance(ManualScheduler(), Scheduler)


def test_interval_scheduler_sleeps_between_ticks() -> None:
    sleeps: list[float] = []
    sched = IntervalScheduler(interval=0.5, sleep=sleeps.append)
    executed = sched.run(lambda i: True, max_ticks=3)
    assert executed == 3
    # Sleeps only happen *between* ticks: 3 ticks -> 2 sleeps.
    assert sleeps == [0.5, 0.5]


def test_interval_scheduler_no_sleep_on_early_stop() -> None:
    sleeps: list[float] = []
    sched = IntervalScheduler(interval=1.0, sleep=sleeps.append)
    executed = sched.run(lambda i: False, max_ticks=5)
    assert executed == 1
    assert sleeps == []


def test_interval_scheduler_rejects_negative_interval() -> None:
    with pytest.raises(ValueError, match="interval"):
        IntervalScheduler(interval=-1.0)


def test_interval_scheduler_satisfies_protocol() -> None:
    assert isinstance(IntervalScheduler(interval=0.0), Scheduler)
