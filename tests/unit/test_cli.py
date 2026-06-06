"""Tests for :mod:`automated_trading_bot.cli`."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from automated_trading_bot import __version__
from automated_trading_bot.cli import app, synthetic_prices

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_strategies_command_lists_all() -> None:
    result = runner.invoke(app, ["strategies"])
    assert result.exit_code == 0
    assert "momentum_ma" in result.stdout
    assert "mean_reversion" in result.stdout
    assert "breakout" in result.stdout


def test_demo_command_runs() -> None:
    result = runner.invoke(app, ["demo", "--strategy", "breakout"])
    assert result.exit_code == 0
    assert "Total return" in result.stdout
    assert "Sharpe" in result.stdout


def test_init_config_and_backtest_roundtrip(tmp_path: Path) -> None:
    profile = tmp_path / "p.json"
    result = runner.invoke(app, ["init-config", str(profile), "--strategy", "mean_reversion"])
    assert result.exit_code == 0
    assert profile.exists()

    result = runner.invoke(app, ["backtest", str(profile), "--bars", "120"])
    assert result.exit_code == 0
    assert "mean_reversion" in result.stdout


def test_run_command_executes_ticks() -> None:
    result = runner.invoke(app, ["run", "--ticks", "40", "--interval", "0"])
    assert result.exit_code == 0
    assert "Ran" in result.stdout
    assert "Final equity" in result.stdout


def test_synthetic_prices_length() -> None:
    assert len(synthetic_prices(n=50)) == 50
