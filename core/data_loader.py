import os
import hashlib
import pandas as pd


def _make_cache_key(symbol: str, start_date: str, end_date: str, source: str) -> str:
    key = f"{symbol}_{start_date}_{end_date}_{source}"
    return hashlib.md5(key.encode()).hexdigest()


def load_price_data(symbol: str, start_date: str, end_date: str,
                    use_cache: bool = True,
                    force_refresh: bool = False,
                    source: str = "yahoo") -> pd.DataFrame:
    """
    Load historical OHLCV data for a given symbol, with cache and source switching.
    """
    os.makedirs("./data_cache", exist_ok=True)
    cache_key = _make_cache_key(symbol, start_date, end_date, source)
    cache_path = os.path.join("./data_cache", f"{cache_key}.parquet")

    # Load from cache
    if use_cache and os.path.exists(cache_path) and not force_refresh:
        try:
            return pd.read_parquet(cache_path)
        except Exception:
            print(f"⚠️ Cache corrupted at {cache_path}, refetching...")

    # Fetch data from appropriate source
    if source == "yahoo":
        from data_ingestion.yahoo_fetcher import fetch_yahoo_data
        df = fetch_yahoo_data(symbol, start_date, end_date)
    elif source == "polygon":
        from data_ingestion.polygon_fetcher import fetch_polygon_data
        df = fetch_polygon_data(symbol, start_date, end_date)
    else:
        raise ValueError(f"Unsupported data source: {source}")

    if df.empty or "Close" not in df.columns:
        raise ValueError(f"No data returned for {symbol} from {start_date} to {end_date}")

    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    df.to_parquet(cache_path)

    return df


class DataIngestionManager:
    def __init__(self, use_cache=True, force_refresh=False, source="yahoo"):
        self.use_cache = use_cache
        self.force_refresh = force_refresh
        self.source = source

    def get_data(self, symbol: str, start_date: str, end_date: str):
        return load_price_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            use_cache=self.use_cache,
            force_refresh=self.force_refresh,
            source=self.source
        )

