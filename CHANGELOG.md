# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/).

## [0.2.0] - 2025

### Added
- Two new strategies alongside the original momentum crossover: a z-score band
  `mean_reversion` strategy and a Donchian-channel `breakout` strategy, plus a
  `Strategy` protocol, a name-keyed `STRATEGIES` registry, and a
  `build_strategy()` factory.
- Richer risk controls in `RiskManager`: a concurrent-position cap
  (`max_positions` / `can_open`) and a daily-loss limit (`daily_loss_limit` /
  `is_halted`). The runner now flattens and stops opening positions once the
  daily-loss limit is breached, with `start_new_day()` to reset the baseline.
- Expanded backtest report: annualised Sharpe ratio, annualised volatility, and
  win rate added to `BacktestResult`, plus a human-readable `report()` renderer.
- JSON config profiles: `BotConfig.from_json` / `from_json_file` /
  `to_json` / `to_json_file` to round-trip a profile to disk.
- A dependency-free scheduler abstraction (`Scheduler` protocol with
  `IntervalScheduler` and a deterministic `ManualScheduler`).
- CLI subcommands: `strategies`, `init-config`, `backtest` (from a JSON
  profile), and `run` (driven by the scheduler), alongside `version` and `demo`.
- `rolling_std()` helper for standard-deviation windows.

### Changed
- `BotRunner` now builds its strategy via `build_strategy()` and enforces the new
  risk guardrails on every bar.
- Roughly doubled the test suite (20 to 74 tests) with real assertions covering
  every new module and code path.

## [0.1.0] - 2025

### Added
- Initial release of automated-trading-bot: Automated trading bot template — config-driven, scheduled, with risk and backtest.
