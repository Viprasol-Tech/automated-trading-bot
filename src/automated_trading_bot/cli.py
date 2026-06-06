"""Command-line interface for Automated Trading Bot.

Subcommands:

* ``version``     — print the installed version.
* ``strategies``  — list the built-in strategies.
* ``init-config`` — write a starter JSON config profile.
* ``demo``        — backtest a strategy on a synthetic price series.
* ``backtest``    — backtest using a JSON config profile.
* ``run``         — drive the bot on a clock via the scheduler abstraction.

Every command is fully offline: no API keys, no network, no real money.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import math
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from automated_trading_bot import __version__
from automated_trading_bot.backtest import run_backtest
from automated_trading_bot.config import BotConfig
from automated_trading_bot.runner import BotRunner
from automated_trading_bot.scheduler import IntervalScheduler
from automated_trading_bot.strategy import STRATEGIES

app = typer.Typer(add_completion=False, help="Automated Trading Bot - by Viprasol Tech.")
console = Console()


def synthetic_prices(n: int = 240, base: float = 100.0) -> list[float]:
    """Return a gently trending, wavy synthetic price series for demos/runs."""
    return [base + 0.15 * i + 8.0 * math.sin(i / 12.0) for i in range(n)]


def _print_result(config: BotConfig, prices: list[float]) -> None:
    """Run a backtest of ``config`` over ``prices`` and pretty-print it."""
    result = run_backtest(config, prices)
    console.print(f"Symbol:        [bold]{config.symbol}[/]")
    console.print(
        f"Strategy:      [cyan]{config.strategy}[/] (fast={config.fast}, slow={config.slow})"
    )
    console.print(f"Risk/position: {config.risk_fraction:.0%} of equity")
    console.print(f"Max positions: {config.max_positions}")
    console.print(f"Daily loss:    {config.daily_loss_limit:.0%}")
    console.print(f"Bars:          {len(prices)}")
    console.print(f"Trades:        {result.num_trades}")
    console.print(f"Total return:  [bold]{result.total_return:+.2%}[/]")
    console.print(f"Max drawdown:  {result.max_drawdown:.2%}")
    console.print(f"Sharpe (ann.): {result.sharpe:.2f}")
    console.print(f"Win rate:      {result.win_rate:.2%}")
    console.print(
        f"Final equity:  [bold green]${result.final_equity:,.2f}[/] "
        f"(started ${result.starting_equity:,.2f})"
    )


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"automated-trading-bot [bold cyan]{__version__}[/] - by Viprasol Tech")


@app.command()
def strategies() -> None:
    """List the built-in strategies."""
    table = Table(title="Available strategies")
    table.add_column("Name", style="cyan")
    table.add_column("Summary")
    for name, cls in sorted(STRATEGIES.items()):
        doc = (cls.__doc__ or "").strip().splitlines()
        summary = doc[0] if doc else ""
        table.add_row(name, summary)
    console.print(table)


@app.command(name="init-config")
def init_config(
    path: Path = typer.Argument(..., help="Where to write the JSON profile."),
    symbol: str = typer.Option("BTC/USDT", help="Instrument symbol."),
    strategy: str = typer.Option("momentum_ma", help="Strategy name."),
) -> None:
    """Write a starter JSON config profile to ``path``."""
    config = BotConfig(symbol=symbol, strategy=strategy)
    config.to_json_file(path)
    console.print(f"Wrote config profile to [bold]{path}[/]")


@app.command()
def demo(
    symbol: str = typer.Option("BTC/USDT", help="Instrument symbol."),
    strategy: str = typer.Option("momentum_ma", help="Strategy name."),
    fast: int = typer.Option(10, help="Fast moving-average window."),
    slow: int = typer.Option(30, help="Slow moving-average window."),
    risk_fraction: float = typer.Option(0.2, help="Equity fraction risked per position."),
) -> None:
    """Backtest a strategy on a synthetic price series."""
    config = BotConfig(
        symbol=symbol, strategy=strategy, fast=fast, slow=slow, risk_fraction=risk_fraction
    )
    _print_result(config, synthetic_prices())


@app.command()
def backtest(
    config_path: Path = typer.Argument(..., help="Path to a JSON config profile."),
    bars: int = typer.Option(240, help="Number of synthetic bars to simulate."),
) -> None:
    """Backtest using a JSON config profile (see ``init-config``)."""
    config = BotConfig.from_json_file(config_path)
    _print_result(config, synthetic_prices(n=bars))


@app.command()
def run(
    symbol: str = typer.Option("BTC/USDT", help="Instrument symbol."),
    strategy: str = typer.Option("momentum_ma", help="Strategy name."),
    ticks: int = typer.Option(60, help="Number of bars to feed the bot."),
    interval: float = typer.Option(0.0, help="Seconds between ticks (0 = no wait)."),
) -> None:
    """Drive the bot on a clock via the scheduler abstraction."""
    config = BotConfig(symbol=symbol, strategy=strategy)
    prices = synthetic_prices(n=ticks)
    runner = BotRunner(config)
    scheduler = IntervalScheduler(interval=interval)

    def tick(i: int) -> bool:
        runner.on_bar(prices[i])
        return not runner.halted

    executed = scheduler.run(tick, max_ticks=len(prices))
    final = runner.equity(prices[executed - 1])
    console.print(f"Ran [bold]{executed}[/] ticks; trades={len(runner.fills)}")
    console.print(f"Final equity: [bold green]${final:,.2f}[/]")
    if runner.halted:
        console.print("[yellow]Trading halted by daily-loss limit.[/]")


if __name__ == "__main__":
    app()
