# Getting Started

## Install

```bash
pip install -r requirements.txt   # or: pip install -e .
```

Core stack: `bt` (engine), `ffn` + `quantstats` (metrics), `yfinance` (data). Requires Python ≥ 3.10 and
pandas ≥ 2.2.

Where this is heading: a universe-first, point-in-time research platform (cross-sectional backtests,
EDGAR fundamentals, screener = a strategy's latest row). See `docs/03-research-platform.md`.

> On this machine the conda env is `options-trading` and the `conda` shell function is broken, so call the
> interpreter by path: `/Users/rchaks/opt/miniforge3/envs/options-trading/bin/python`.

## Run a backtest

```bash
python run.py --strategy=momentum --tickers=AAPL --benchmark=SPY --start=2023-01-01 --end=2024-01-01 --out=output/momentum
```

Flags: `--strategy` (`buy_n_hold` | `momentum` | `xs_momentum`), `--tickers` (comma-separated) **or**
`--universe sp500`, `--benchmark`, `--start`, `--end`, `--cash`, `--source` (`yahoo` | `polygon` | `alpaca`),
`--interval`, `--out`. `xs_momentum` is cross-sectional momentum: rank a basket by trailing return, hold the
top names equal-weighted, reconstituted monthly — give it several tickers.

## Sweep a single-asset rule across a universe

`momentum` is a *single-asset* rule — running it on one hand-picked ticker is a cherry-pick (selection bias).
To judge it honestly, sweep it across a whole universe and look at the **distribution** of alpha/beta:

```bash
python sweep.py --strategy=momentum --universe=sp500 --benchmark=SPY --start=2019-01-01 --end=2024-01-01 --out=output/sweep
```

Paste the S&P 500 constituents into `data/sp500.csv` first (a `Symbol` column, optionally `GICS Sector` /
`GICS Sub-Industry`); use `--limit N` for a quick run on the first N names. It writes `per_name_metrics.csv`,
`distribution_summary.csv` (median alpha/beta, % of names that beat the benchmark), and an interactive
`alpha_beta_distribution.html`. Every artifact is stamped with the universe's survivorship-bias caveat.
Running a single-asset strategy through `run.py --universe` is refused with a pointer here.

**Rebalance / reconstitution (optional):** `--rebalance` and `--reconstitute` take `D|W|M|Q|Y` and override the
strategy's defaults (both daily = trade whenever the signal changes). `--rebalance Q` trades back to target
quarterly; `--reconstitute Y` recomputes the target (selection + weights) yearly and holds it constant in
between. A strategy can also set these as class attributes (`rebalance_freq`, `reconstitution_freq`).

**Risk guardrail (optional):** add `--stop-loss 0.05` for a 5% stop (configurable). It's trailing by default
(stop measured from the peak since entry); use `--stop-loss-mode fixed` to stop from the entry price instead.
Because we only have daily bars, a breach is detected on a day's close and the exit lands on the next close —
no intraday or optimistic stop-price fills. A stopped ticker goes to cash and stays out until the strategy
re-enters it.

```bash
python run.py --strategy=momentum --tickers=AAPL --benchmark=SPY --start=2022-01-01 --end=2024-01-01 --stop-loss=0.05
```

Artifacts written to `--out`:

| File | Contents |
|------|----------|
| `equity_curve.csv` | Strategy and benchmark equity (NAV) per day |
| `daily_returns.csv` | Daily returns |
| `stats.csv` | `bt` performance table (CAGR, Sharpe, max drawdown, …) |
| `metrics.csv` | quantstats metrics vs benchmark (alpha, beta, Sortino, VaR, win rates, …) |
| `equity_vs_benchmark.png` | Rebased equity vs benchmark |
| `drawdown.png` | Strategy drawdown |
| `tearsheet.html` | Full quantstats tearsheet (distribution, rolling Sharpe, alpha/beta, risk) |
| `equity_explorer.html` | Interactive: equity + underlying prices + buy/sell markers; hover shows the portfolio split that day |

## How it fits together

`data → price panel → strategy weights → bt → reports`

- `core/data_loader.py` — `DataIngestionManager.get_data()` fetches OHLCV (cached as parquet).
- `core/price_panel.py` — `to_price_panel()` builds the tz-naive close-price panel `bt` trades.
- `strategies/` — a strategy maps the panel to **target weights**.
- `engine/runner.py` — `run()` executes the strategy + a buy-and-hold benchmark on `bt`.
- `reporting/report.py` — `write_reports()` writes the artifacts above.

## Add a strategy

Subclass `TargetWeightStrategy` and return target weights. Apply any signal lag *inside* `weights()` so the
strategy never looks ahead.

```python
# strategies/my_strategy.py
import pandas as pd
from strategies.base import TargetWeightStrategy, register

@register("my_strategy")
class MyStrategy(TargetWeightStrategy):
    name = "my_strategy"

    def weights(self, prices: pd.DataFrame) -> pd.DataFrame:
        signal = (prices > prices.rolling(50).mean()).astype(float)
        weights = signal.div(signal.sum(axis=1).where(lambda s: s > 0), axis=0).fillna(0.0)
        return weights.shift(1).fillna(0.0)   # decide on t, act on t+1
```

Then import it in `strategies/__init__.py` and ship a no-look-ahead test (see `tests/test_no_lookahead.py`):
truncating future rows must not change a past weight.

## Paper trading

`paper_trade.py` rebalances an **Alpaca paper** account toward the strategy's *current* target weights — same
strategy / guardrail / frequency flags as the backtest. It **previews by default** (prints the order plan and
submits nothing); add `--execute` to actually send the orders.

```bash
# preview
python paper_trade.py --strategy=momentum --tickers=AAPL,MSFT --stop-loss=0.05
# actually submit to Alpaca paper
python paper_trade.py --strategy=momentum --tickers=AAPL,MSFT --stop-loss=0.05 --execute
```

It reads `ALPACA_API_KEY` / `ALPACA_API_SECRET` from `.env`, talks to the REST API over `requests` (paper host
only — asserted), sizes whole-share market orders against your account equity, and sells before buying so
closing trades fund the openings. To automate, run it on a schedule (cron / `/schedule`) — there's no daemon.

## Test

```bash
python -m pytest tests/ -q
```
