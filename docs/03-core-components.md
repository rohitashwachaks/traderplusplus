# Core Components

Deep dive into the core engine components: Backtester, MarketData, and DataLoader.

## 🔄 Backtester

**Location**: [`core/backtester.py`](../core/backtester.py)

The Backtester orchestrates the event-driven simulation loop.

### Key Methods

#### `run(start_date, end_date, interval='1d', period='5y')`
Executes the backtest simulation.

#### `get_trade_log() -> pd.DataFrame`
Returns complete trade history.

#### `get_equity_curve() -> pd.DataFrame`
Returns portfolio value over time.

#### `get_final_net_worth() -> float`
Returns final portfolio value.

### Usage Example

```python
from core.backtester import Backtester

backtester = Backtester(
    strategy=portfolio.strategy,
    market_data=market_data,
    portfolio=portfolio,
    executor=executor
)

backtester.run(start_date="2023-01-01", end_date="2024-01-01")
print(backtester.get_trade_log())
```

## 📊 MarketData

**Location**: [`core/market_data.py`](../core/market_data.py)

Provides time-series price data with no-look-ahead guarantees.

### Key Methods

#### `get_market_data(tickers, end_date, start_date=None, interval='1d', period='5y')`
Fetches and validates market data.

#### `get_price(ticker, date, price_type='Close') -> Dict[str, float]`
Returns price for ticker(s) at specific date.

#### `get_history(ticker_list, end_date, lookback) -> Dict[str, pd.DataFrame]`
Returns historical data for lookback period.

#### `get_series(ticker, price_type='Close') -> pd.Series`
Returns complete price series.

### Properties

#### `dates -> pd.DatetimeIndex`
Returns common date index for simulation.

## 💾 DataIngestionManager

**Location**: [`core/data_loader.py`](../core/data_loader.py)

Handles data fetching from external sources with caching.

### Key Methods

#### `get_data(tickers, end_date, start_date=None, interval='1d', period='5y') -> Dict[str, pd.DataFrame]`
Fetches data for multiple tickers.

### Caching System

Cache keys are MD5 hashes stored as Parquet files in `./data_cache/`.

**Force Refresh**:
```python
ingestion = DataIngestionManager(force_refresh=True)
```

**Clear Cache**:
```bash
rm -rf ./data_cache
```

## 📚 Related Documentation

- [Getting Started](./02-getting-started.md)
- [Contracts & Data Models](./04-contracts.md)
- [Strategy Development](./05-strategies.md)
- [API Reference](./11-api-reference.md)

---

**Code References**:
- [`core/backtester.py`](../core/backtester.py)
- [`core/market_data.py`](../core/market_data.py)
- [`core/data_loader.py`](../core/data_loader.py)
