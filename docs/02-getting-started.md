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

Flags: `--strategy` (`buy_n_hold` | `momentum` | `xs_momentum` | `dual_momentum` | `ls_pe` |
`sector_neutral_momentum`), `--tickers` (comma-separated) **or** `--universe sp500` (with `--limit N` for quick
runs), `--benchmark`, `--start`, `--end`, `--cash`, `--source` (`yahoo` | `polygon` | `alpaca`), `--interval`,
`--out`, `--cost-bps` (commission+slippage per trade in bps of notional; `0` — the default — is frictionless
and **stamped** as such on every artifact), `--group-by` (classification key for a grouping strategy).

Daily prices are served from the canonical store (`data_store/`): the first run fetches and ingests, every
later run reads locally and fetches only new dates — re-running a backtest downloads nothing. Each output
directory carries a `manifest.json` (git SHA, args, universe fingerprint, bias stamps) so any result folder is
self-describing and re-derivable. `xs_momentum` is cross-sectional momentum (rank a
basket by trailing return, hold the top names equal-weighted, monthly). `ls_pe` is a dollar-neutral long/short
on **point-in-time P/E** (long cheapest, short richest) — it pulls annual EPS from SEC EDGAR, keyed to filing
date, so give it a universe (e.g. `--universe sp500 --limit 50`).

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

**Risk guardrail (optional):** add `--stop-loss 0.05` for a 5% stop (configurable). It's trailing by default;
use `--stop-loss-mode fixed` to stop from the entry price instead. The stop models a resting stop order as
faithfully as daily bars allow: the reference **trails the intraday high**, the stop **triggers the day the
intraday low touches the level**, and the exit **fills at that same day's close** — immediately, even if the
strategy rebalances monthly or quarterly (risk exits never wait for the schedule). Fill realism is stamped,
not hidden: `bt` fills at closes, so a gap *through* the stop books the crash day's close (worse than a real
stop fill — conservative), while a touch-and-recover day books the recovered close (slightly optimistic). A
stopped ticker goes to cash and stays out until the strategy's own signal goes flat and re-fires — **or**, with
`--stop-reentry N`, until N trading days pass and the signal still wants the name (the stop re-arms from the
re-entry price). Use the cooldown with slow signals like SMA crossovers: a crash can trip the stop while the
crossover never goes flat, and without re-entry the name would sit in cash through the whole recovery. The
cost is symmetric: in a persistent decline the cooldown re-buys a falling name once every N days. The equity
explorer draws the **active stop level** (dashed red) next to each held name, so you can see the intended
exit against the actual one.

```bash
python run.py --strategy=momentum --tickers=AAPL --benchmark=SPY --start=2022-01-01 --end=2024-01-01 --stop-loss=0.05
```

A strategy can also **ship with guardrails attached** — set the `guardrails` attribute (a tuple of `Guardrail`
instances) on the class or instance and they apply on every run, backtest and paper alike; CLI guardrails are
added after them.

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
| `equity_explorer.html` | Interactive: **cumulative return %** (breakeven = 0%) vs benchmark + underlying names, with a drawdown panel, a range **slider** and 1M/3M/6M/YTD/1Y/All buttons. Hover shows the portfolio split and the actual **dollar price** on each line — including the fill price at every buy/sell marker. |

## Cross-industry strategies (sector / SIC classification)

Each ticker carries a static classification in `ctx.meta`, so a strategy can rank and select **within**
industries instead of letting one hot sector dominate. Two taxonomies, one source of truth each:

- **GICS `sector` / `industry`** (GICS Sub-Industry) — from `data/sp500.csv`, so it's free and offline but
  **only exists for `--universe sp500`**.
- **SIC `sic` / `sic_description` / `sic2`** (2-digit major group) — from SEC EDGAR, so it works for **any**
  US-filer universe. Pulled on demand when a `sic*` key is requested.

`sector_neutral_momentum` holds the top trailing-return name in *each* group, so the book always spans
industries:

```bash
# GICS sectors (SP500, no extra fetch)
python run.py --strategy=sector_neutral_momentum --universe=sp500 --benchmark=SPY --start=2019-01-01 --end=2024-01-01
# EDGAR SIC major groups — works on any universe
python run.py --strategy=sector_neutral_momentum --tickers=AAPL,XOM,JPM,PFE,CAT --group-by=sic2 --benchmark=SPY --start=2019-01-01 --end=2024-01-01
```

The run logs the group breakdown, writes the full ticker→classification table to `classification.csv`, and
**stamps every artifact**: the labels are *static* (today's GICS/SIC applied to all history — sector
reclassification over time is unmodeled), a labeled bias in the same family as survivorship.

To group inside your own strategy, set `requires_meta = ("sector",)` and use `strategies/grouping.py`:

```python
from strategies import grouping

groups = grouping.group_series(ctx, self.group_by)          # ticker → label, aligned to columns
picks = grouping.top_per_group(signal, groups, n=1)         # top-1 per group each day (bool panel)
```

## How it fits together

`data → DataContext → strategy weights → bt → reports`

- `core/data_loader.py` — `DataIngestionManager.get_data()` fetches OHLCV (cached as parquet).
- `core/sources.py` + `core/context.py` — `build_context()` assembles a `DataContext` (price + any extra
  panels a strategy declares), outer-joining the universe and forward-filling fundamentals point-in-time.
- `core/universe.py` — the tradable set (`SP500` from `data/sp500.csv`) and its membership mask.
- `strategies/` — a strategy maps the `DataContext` to **target weights**.
- `engine/runner.py` — `run()` executes the strategy + a buy-and-hold benchmark on `bt`.
- `reporting/report.py` — `write_reports()` writes the artifacts above.

## Add a strategy

Subclass `TargetWeightStrategy`, read data through the `DataContext`, and return target weights. Apply any
signal lag *inside* `weights()` so the strategy never looks ahead, and only hold names where `ctx.members` is
true. Declare any non-price data via `requires` — available panels: `eps` (annual, as-first-filed), `eps_ttm`
(trailing-twelve-month, Q4 reconstructed from the 10-K), `shares` (shares outstanding; market cap is
`ctx.price * ctx.fundamental("shares")`).

```python
# strategies/my_strategy.py
import pandas as pd
from core.context import DataContext
from strategies.base import TargetWeightStrategy, register

@register("my_strategy")
class MyStrategy(TargetWeightStrategy):
    name = "my_strategy"
    requires = ()                       # extra context panels, e.g. ("eps",)

    def weights(self, ctx: DataContext) -> pd.DataFrame:
        prices = ctx.price.where(ctx.members)            # only in-universe names
        signal = (prices > prices.rolling(50).mean()).astype(float)
        weights = signal.div(signal.sum(axis=1).where(lambda s: s > 0), axis=0).fillna(0.0)
        return weights.shift(1).fillna(0.0)              # decide on t, act on t+1
```

Then import it in `strategies/__init__.py` and ship a no-look-ahead test (see `tests/test_no_lookahead.py`):
truncating future rows must not change a past weight. A *single-asset* rule sets `single_asset = True` and is
validated with `sweep.py` instead of being pooled into a basket.

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
closing trades fund the openings. Every run — preview or executed — is appended to a JSONL **journal**
(`output/paper/journal.jsonl`); after fills settle, `python paper_trade.py --reconcile` diffs the broker's
actual orders against the last executed plan and reports per-order slippage in bps. Scheduling (launchd — no
server needed), timing that matches the backtest's execution lag, and the full ops guide live in
[`05-paper-trading.md`](./05-paper-trading.md).

## Test

```bash
python -m pytest tests/ -q
```
