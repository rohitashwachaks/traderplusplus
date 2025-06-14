import os
import hashlib
import pandas as pd
from typing import Dict, List


def _make_cache_key(ticker: str, start_date: str, end_date: str, source: str) -> str:
    key = f"{ticker}_{start_date}_{end_date}_{source}"
    return hashlib.md5(key.encode()).hexdigest()


def _fetch_data(ticker: str, start_date: str, end_date: str, source: str) -> pd.DataFrame:
    if source == "yahoo":
        from data_ingestion.yahoo_fetcher import fetch_yahoo_data
        return fetch_yahoo_data(ticker, start_date, end_date)
    elif source == "alpaca":
        from data_ingestion.alpaca_fetcher import fetch_alpaca_data
        return fetch_alpaca_data(ticker, start_date, end_date)
    elif source == "polygon":
        from data_ingestion.polygon_fetcher import fetch_polygon_data
        return fetch_polygon_data(ticker, start_date, end_date)
    else:
        raise ValueError(f"Unsupported data source: {source}. Supported sources are 'yahoo', 'alpaca', and 'polygon'.")


def load_price_data(ticker: str, start_date: str, end_date: str,
                    use_cache: bool = True,
                    force_refresh: bool = False,
                    source: str = "yahoo") -> pd.DataFrame:
    """
    Load historical OHLCV data for a single ticker from the specified data source.

    Args:
        ticker (str): The ticker symbol of the security.
        start_date (str): The start date of the data range.
        end_date (str): The end date of the data range.
        use_cache (bool, optional): Whether to use cached data. Defaults to True.
        force_refresh (bool, optional): Whether to force a refresh of the data. Defaults to False.
        source (str, optional): The data source to use. Defaults to "yahoo".

    Returns:
        pd.DataFrame: A pandas DataFrame containing the historical OHLCV data.
    """
    os.makedirs("./data_cache", exist_ok=True)
    cache_key = _make_cache_key(ticker, start_date, end_date, source)
    cache_path = os.path.join("./data_cache", f"{cache_key}.parquet")

    if use_cache and os.path.exists(cache_path) and not force_refresh:
        try:
            return pd.read_parquet(cache_path)
        except Exception:
            print(f"⚠️ Cache corrupted at {cache_path}, refetching...")

    df = _fetch_data(ticker, start_date, end_date, source)

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

    def get_data(self, tickers: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame] | pd.DataFrame:
        """
        Return a dictionary of {ticker: DataFrame} for all requested tickers.

        Args:
            tickers (List[str]): A list of ticker symbols.
            start_date (str): The start date of the data range.
            end_date (str): The end date of the data range.

        Returns:
            Dict[str, pd.DataFrame]: A dictionary containing the historical OHLCV data for each ticker.
        """
        # TODO: Convert Dict structure to a single Multi-indexed dataframe?
        # data = load_price_data(
        #         tickers,
        #         start_date,
        #         end_date,
        #         use_cache=self.use_cache,
        #         force_refresh=self.force_refresh,
        #         source=self.source
        #     )
        data = {}
        for ticker in tickers:
            data[ticker] = load_price_data(
                ticker,
                start_date,
                end_date,
                use_cache=self.use_cache,
                force_refresh=self.force_refresh,
                source=self.source
            )
        return data
