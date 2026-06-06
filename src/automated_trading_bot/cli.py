"""Command-line interface for Automated Trading Bot.

``automated-trading-bot demo`` builds a :class:`BotConfig`, generates a synthetic
trending price series, and runs a full backtest of the moving-average momentum
strategy — no API keys, no network, no risk.

Part of Automated Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import math

import typer
from rich.console import Console

from automated_trading_bot import __version__
from automated_trading_bot.backtest import run_backtest
from automated_trading_bot.config import BotConfig

app = typer.Typer(add_completion=False, help="Automated Trading Bot — by Viprasol Tech.")
console = Console()


def _synthetic_prices(n: int = 240, base: float = 100.0) -> list[float]:
    """Return a gently trending, wavy synthetic price series for the demo."""
    return [base + 0.15 * i + 8.0 * math.sin(i / 12.0) for i in range(n)]


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"automated-trading-bot [bold cyan]{__version__}[/] — by Viprasol Tech")


@app.command()
def demo(
    symbol: str = typer.Option("BTC/USDT", help="Instrument symbol."),
    fast: int = typer.Option(10, help="Fast moving-average window."),
    slow: int = typer.Option(30, help="Slow moving-average window."),
    risk_fraction: float = typer.Option(0.2, help="Equity fraction risked per position."),
) -> None:
    """Backtest the momentum strategy on a synthetic price series."""
    config = BotConfig(symbol=symbol, fast=fast, slow=slow, risk_fraction=risk_fraction)
    prices = _synthetic_prices()
    result = run_backtest(config, prices)

    console.print(f"Symbol:        [bold]{config.symbol}[/]")
    console.print(f"Strategy:      momentum_ma (fast={config.fast}, slow={config.slow})")
    console.print(f"Risk/position: {config.risk_fraction:.0%} of equity")
    console.print(f"Bars:          {len(prices)}")
    console.print(f"Trades:        {result.num_trades}")
    console.print(f"Total return:  [bold]{result.total_return:+.2%}[/]")
    console.print(f"Max drawdown:  {result.max_drawdown:.2%}")
    console.print(
        f"Final equity:  [bold green]${result.final_equity:,.2f}[/] "
        f"(started ${result.starting_equity:,.2f})"
    )


if __name__ == "__main__":
    app()
