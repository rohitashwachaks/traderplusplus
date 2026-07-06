# Data Ingestion & Sources

Guide to data fetching, caching, and integration with market data providers.

## 📋 Overview

Trader++ supports multiple data sources:
- **Yahoo Finance**: Free, no API key required
- **Alpaca**: Real-time data, broker integration
- **Polygon**: High-quality institutional data

All data is cached locally in Parquet format.

**Location**: [`data_ingestion/`](../data_ingestion/)

## 📊 Data Format

All sources return standardized OHLCV DataFrames:

```python
                    Open    High     Low   Close    Volume
Date                                                      
2023-01-03 00:00:00  125.07  125.35  124.17  125.07  112117500
```

**Required Columns**: Open, High, Low, Close, Volume  
**Index**: DatetimeIndex (UTC timezone)

## 🌐 Yahoo Finance

**Location**: [`data_ingestion/yahoo_fetcher.py`](../data_ingestion/yahoo_fetcher.py)

### Usage

```python
from core.data_loader import DataIngestionManager

ingestion = DataIngestionManager(source="yahoo")
data = ingestion.get_data(
    tickers=["AAPL", "MSFT"],
    start_date="2023-01-01",
    end_date="2024-01-01"
)
```

### CLI

```bash
python run.py --source=yahoo --tickers=AAPL
```

**Pros**: Free, global coverage  
**Cons**: Rate limits, occasional downtime

## 🔷 Alpaca

**Location**: [`data_ingestion/alpaca_fetcher.py`](../data_ingestion/alpaca_fetcher.py)

### Requirements

```bash
export ALPACA_API_KEY="your_api_key"
export ALPACA_SECRET_KEY="your_secret_key"
```

### Usage

```python
ingestion = DataIngestionManager(source="alpaca")
```

**Pros**: Real-time, broker integration  
**Cons**: Requires API key, US markets only

## 🔶 Polygon

**Location**: [`data_ingestion/polygon_fetcher.py`](../data_ingestion/polygon_fetcher.py)

### Requirements

```bash
export POLYGON_API_KEY="your_api_key"
```

### Usage

```python
ingestion = DataIngestionManager(source="polygon")
```

**Pros**: Institutional quality, extensive coverage  
**Cons**: Requires paid API key

## 💾 Storage — canonical store + legacy cache

**Daily bars live in the canonical price store** (`./data_store/`, override via `DATA_STORE`):
one additive parquet file per ticker plus `coverage.json` recording the calendar window each
ticker already holds. `PriceStore.ensure()` fetches **only the gap** between what's stored and
what a run needs — re-running any backtest downloads nothing, and widening the window fetches
just the new dates. One vendor per ticker (mixing sources would let two runs silently
disagree); `PriceStore().forget("AAPL")` drops a series for a clean refetch — useful because
adjusted prices are retroactively restated by splits/dividends. See `core/store.py`.

**Intraday (non-`1d`) requests** still go through the legacy per-request MD5 cache
(`./data_cache/`, override via `DATA_CACHE`) — intraday is out of the platform's scope, so it
never earned a canonical store. EDGAR responses cache under `data_store/edgar/` and
`data_cache/`. Everything is regenerable: deleting either directory just refetches.

## 🔧 Custom Data Sources

Two extension points, depending on what you're adding:

**A new price vendor** (another OHLCV feed): write a fetcher returning the standard OHLCV
frame and add a branch for it in `core/data_loader._fetch_data` — the store and every panel
pick it up via `--source`.

**A new kind of data** (a fundamental, a sentiment score, anything point-in-time): implement a
`PanelSource` and register it — strategies opt in via `requires`, with zero engine changes:

```python
# core/my_panel.py
from core.sources import PanelSource, register_source

class MySource(PanelSource):
    name = "my_signal"                       # strategies declare requires=("my_signal",)

    def load(self, tickers, start, end, **opts) -> pd.DataFrame:
        # sparse dates×tickers frame, each value indexed by the date it became PUBLIC;
        # build_context forward-fills it onto the trading calendar (past-only, no look-ahead)
        ...

register_source(MySource())
```

## 🧱 From OHLCV to the DataContext

The OHLCV fetchers above are the *raw* layer. Strategies don't read them directly — they read a
**`DataContext`** assembled by `core/context.build_context()`. Two pieces sit in between:

- **`core/sources.py` — `PanelSource` registry.** Each source produces one named `dates × tickers` panel and
  registers under that name. `PriceSource` wraps the OHLCV fetchers above to serve the `price` panel;
  `core/fundamentals.EpsSource` serves the `eps` panel from SEC EDGAR. Add a source → it's available as
  `ctx.panel("name")` with **zero strategy changes**.
- **`core/context.py` — `DataContext`.** One object exposing `ctx.price`, `ctx.members` (the membership mask),
  `ctx.meta` (sector/SIC), and `ctx.fundamental(name)`. `build_context` outer-joins the universe (names with
  staggered listing histories are kept as NaN, not dropped), sets `members = membership & price.notna()` (a
  name is only held when it actually traded), and forward-fills feature panels from their availability date —
  **point-in-time, no look-ahead.**

### Universe (`core/universe.py`)

`SP500` reads constituents from `data/sp500.csv` (paste them in; a committed file is deterministic). It is
**survivorship-biased** (today's members, all-`True` mask) and stamps every report accordingly. `ListUniverse`
wraps an explicit ticker list the same way.

### Point-in-time fundamentals: SEC EDGAR (`data_ingestion/edgar_fetcher.py`, `core/fundamentals.py`)

Fundamentals come **only** from SEC EDGAR, keyed to each value's **`filed`** date so a backtest sees only what
was public then. `edgar_fetcher` maps ticker→CIK (the SEC map overlaid with the `CIK` column committed in
`data/sp500.csv` — no mismatch, no extra network) and pulls cached facts (descriptive User-Agent, polite rate
limit, 404 cached as empty, other HTTP errors raise). What's available:

- **`eps`** — annual diluted EPS, **as-first-filed** (restatements ignored), falling back to basic EPS when
  diluted was never tagged.
- **`eps_ttm`** — trailing-twelve-month EPS; the never-filed Q4 is reconstructed from the 10-K
  (`Q4 = FY − Q1 − Q2 − Q3`) and placed on the 10-K's filing date — point-in-time by construction.
- **`shares`** — common shares outstanding from every 10-K/10-Q cover; market cap is
  `ctx.price * ctx.fundamental("shares")`.
- **`fetch_company_facts(cik)`** — the *full* 10-K/10-Q line-item history (every XBRL concept: revenue, net
  income, assets, …), one long frame indexed by `filed` date, cached to `data_store/edgar/`. The structured
  ingest for financial statements; build new panels from it.
- **`fetch_submissions(cik)` / `fundamentals.sic_meta(tickers)`** — SIC code + description per company, for
  sector-neutral books and comparables.

A strategy opts in via `requires = ("eps",)` (or `eps_ttm`, `shares`). See `docs/03-research-platform.md`.

## 🎯 Best Practices

1. **Use Caching**: Always enable for faster development
2. **Handle Missing Data**: Check for data availability
3. **Choose Appropriate Intervals**: Daily for long periods, minute for short
4. **Respect Rate Limits**: Add delays between requests
5. **Validate Data Quality**: Check for NaN and zero prices

## 🔍 Troubleshooting

### "No data returned"
- Verify ticker symbol
- Check date range has trading days
- Try different source

### "Cache corrupted"
```bash
rm -rf ./data_cache
```

### "Rate limit exceeded"
- Add delays
- Use caching
- Switch to paid API

## 📚 Related Documentation

- [Direction & Roadmap](./00-direction.md)
- [Getting Started](./02-getting-started.md)
- [Research Platform](./03-research-platform.md) — DataContext, universe, point-in-time fundamentals
- [Backlog & Open Decisions](./04-backlog.md)

---

**Code References**:

- [`core/data_loader.py`](../core/data_loader.py) — fetch dispatch + parquet cache
- [`core/sources.py`](../core/sources.py), [`core/context.py`](../core/context.py) — PanelSource registry + DataContext
- [`core/universe.py`](../core/universe.py), [`core/fundamentals.py`](../core/fundamentals.py) — universe + point-in-time EPS
- [`data_ingestion/`](../data_ingestion/) — `yahoo_fetcher.py`, `alpaca_fetcher.py`, `polygon_fetcher.py`, `edgar_fetcher.py`
