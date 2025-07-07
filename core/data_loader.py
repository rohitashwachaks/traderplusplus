import os
import hashlib
from datetime import datetime, timedelta

import pandas as pd
from typing import Dict, List, Optional

from utils.config import DATA_CACHE
from utils.utils import period_to_timedelta


def _make_cache_key(*args, **kwargs) -> str:
    key = '_'.join(args)
    return hashlib.md5(key.encode()).hexdigest()


def _fetch_data(ticker: str, start_date: str, end_date: str, interval: str, source: str) -> pd.DataFrame:
    if source == "yahoo":
        from data_ingestion.yahoo_fetcher import fetch_yahoo_data
        return fetch_yahoo_data(ticker, start_date, end_date, interval)
    elif source == "alpaca":
        from data_ingestion.alpaca_fetcher import fetch_alpaca_data
        return fetch_alpaca_data(ticker, start_date, end_date, interval)
    elif source == "polygon":
        from data_ingestion.polygon_fetcher import fetch_polygon_data
        return fetch_polygon_data(ticker, start_date, end_date, interval)
    else:
        raise ValueError(f"Unsupported data source: {source}. Supported sources are 'yahoo', 'alpaca', and 'polygon'.")


def load_price_data(ticker: str, end_date: str,
                    start_date: Optional[str] = None,
                    interval: str = '1d',
                    use_cache: bool = True,
                    force_refresh: bool = False,
                    source: str = "yahoo") -> pd.DataFrame:
    """
    Load historical OHLCV data for a single ticker from the specified data source.

    Args:
        ticker (str): The ticker of the security.
        end_date (str): The end date of the data range.
        start_date (str, optional): The start date of the data range.
        interval (str): The data interval.
        period (int): The data period.
        use_cache (bool, optional): Whether to use cached data. Defaults to True.
        force_refresh (bool, optional): Whether to force a refresh of the data. Defaults to False.
        source (str, optional): The data source to use. Defaults to "yahoo".

    Returns:
        pd.DataFrame: A pandas DataFrame containing the historical OHLCV data.
    """
    os.makedirs(DATA_CACHE, exist_ok=True)
    cache_key = _make_cache_key(ticker, start_date, end_date, interval, source)
    cache_path = os.path.join(DATA_CACHE, f"{cache_key}.parquet")

    if use_cache and os.path.exists(cache_path) and not force_refresh:
        try:
            return pd.read_parquet(cache_path)
        except Exception:
            print(f"⚠️ Cache corrupted at {cache_path}, refetching...")

    df = _fetch_data(ticker, start_date, end_date, interval, source)

    try:
        df.index = df.index.tz_localize("UTC")
    except:
        df.index = df.index.tz_convert("UTC")

    if df.empty or "Close" not in df.columns:
        raise ValueError(f"No data returned for {ticker} from {start_date} to {end_date}")

    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    df.index = pd.to_datetime(df.index)
    df.to_parquet(cache_path)

    return df


class DataIngestionManager:
    def __init__(self, use_cache=True, force_refresh=False, source="yahoo"):
        self.use_cache = use_cache
        self.force_refresh = force_refresh
        self.source = source

    def get_data(
            self, tickers: List[str], end_date: str, start_date: Optional[str] = None,
            interval: Optional[str] = '1d', period: Optional[int] = '5y',
    ) -> Dict[str, pd.DataFrame] | pd.DataFrame:
        """
        Return a dictionary of {ticker: DataFrame} for all requested tickers.

        Args:
            tickers (List[str]): A list of ticker symbols.
            start_date (str): The start date of the data range.
            end_date (str): The end date of the data range.
            interval (str): The data interval.
            period (int): The data period.

        Returns:
            Dict[str, pd.DataFrame]: A dictionary containing the historical OHLCV data for each ticker.
        """
        start = pd.to_datetime(start_date) if start_date else datetime.today().date()
        end = pd.to_datetime(end_date) if end_date else datetime.today().date()

        # IF start after end
        # OR, if interval in minutes, but period > 60
        if start >= end:
            period_int = period_to_timedelta(period)
            start -= period_int
            start_date = start.strftime('%Y-%m-%d')

        elif interval.endswith("m") and (end - start).days >= 60:  # Yahoo-finance limitation
            start = end - timedelta(days=59)
            start_date = start.strftime('%Y-%m-%d')

        data = {}
        # TODO: Convert Dict structure to a single Multi-indexed dataframe?
        # data = load_price_data(
        #         tickers,
        #         start_date,
        #         end_date,
        #         use_cache=self.use_cache,
        #         force_refresh=self.force_refresh,
        #         source=self.source
        #     )
        for ticker in tickers:
            data[ticker] = load_price_data(
                ticker,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                use_cache=self.use_cache,
                force_refresh=self.force_refresh,
                source=self.source
            )
        return data
