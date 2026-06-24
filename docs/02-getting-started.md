# Getting Started

## Install

```bash
pip install -r requirements.txt   # or: pip install -e .
```

Core stack: `bt` (engine), `ffn` + `quantstats` (metrics), `yfinance` (data). Requires Python ≥ 3.10 and
pandas ≥ 2.2.

> On this machine the conda env is `options-trading` and the `conda` shell function is broken, so call the
> interpreter by path: `/Users/rchaks/opt/miniforge3/envs/options-trading/bin/python`.

## Run a backtest

```bash
python run.py --strategy=momentum --tickers=AAPL --benchmark=SPY --start=2023-01-01 --end=2024-01-01 --out=output/momentum
```

Flags: `--strategy` (`buy_n_hold` | `momentum`), `--tickers` (comma-separated), `--benchmark`, `--start`,
`--end`, `--cash`, `--source` (`yahoo` | `polygon` | `alpaca`), `--interval`, `--out`.

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

## Test

```bash
python -m pytest tests/ -q
```
