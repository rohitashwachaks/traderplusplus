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

## 💾 Caching System

### Cache Location

Default: `./data_cache/`

Configure:
```bash
export DATA_CACHE="/path/to/cache"
```

### Cache Management

**Force Refresh**:
```python
ingestion = DataIngestionManager(force_refresh=True)
```

**CLI**:
```bash
python run.py --refresh
```

**Clear Cache**:
```bash
rm -rf ./data_cache
```

## 🔧 Custom Data Sources

### Step 1: Create Fetcher

```python
# data_ingestion/custom_fetcher.py
def fetch_custom_data(ticker, start_date, end_date, interval):
    # Fetch from your source
    data = your_api.get_data(ticker, start_date, end_date)
    
    # Convert to standard format
    df = pd.DataFrame({
        'Open': data['open'],
        'High': data['high'],
        'Low': data['low'],
        'Close': data['close'],
        'Volume': data['volume']
    }, index=pd.to_datetime(data['timestamp']))
    
    df.index = df.index.tz_localize("UTC")
    return df
```

### Step 2: Register in DataLoader

```python
# core/data_loader.py
def _fetch_data(ticker, start_date, end_date, interval, source):
    if source == "custom":
        from data_ingestion.custom_fetcher import fetch_custom_data
        return fetch_custom_data(ticker, start_date, end_date, interval)
```

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

- [Getting Started](./02-getting-started.md)
- [Core Components](./03-core-components.md)
- [Strategy Development](./05-strategies.md)
- [API Reference](./11-api-reference.md)

---

**Code References**:
- [`core/data_loader.py`](../core/data_loader.py)
- [`data_ingestion/yahoo_fetcher.py`](../data_ingestion/yahoo_fetcher.py)
- [`data_ingestion/alpaca_fetcher.py`](../data_ingestion/alpaca_fetcher.py)
- [`data_ingestion/polygon_fetcher.py`](../data_ingestion/polygon_fetcher.py)
