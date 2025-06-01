# core/market_data.py
import pandas as pd
from typing import Dict, Any, List

from core.data_loader import DataIngestionManager


class MarketData:
    REQUIRED_COLUMNS = ['Open', 'High', 'Low', 'Close', 'Volume']

    def __init__(self, data: Dict[str, pd.DataFrame]):
        self.data = data
        self._validate_all_data()

    def _validate_all_data(self):
        for ticker, df in self.data.items():
            if not isinstance(df, pd.DataFrame):
                raise TypeError(f"Data for {ticker} must be a DataFrame, got {type(df)}")
            if not isinstance(df.index, pd.DatetimeIndex):
                raise ValueError(f"{ticker} DataFrame index must be a DatetimeIndex")
            missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                raise ValueError(f"{ticker} is missing required columns: {missing_cols}")

    @classmethod
    def from_ingestion(cls,
                       tickers: List[str],
                       start_date: str,
                       end_date: str,
                       ingestion_manager: DataIngestionManager) -> 'MarketData':
        """
        Create MarketData by fetching from a DataIngestionManager.
        """
        tickers = [t.strip().upper() for t in tickers]
        raw_data = ingestion_manager.get_data(tickers, start_date, end_date)
        return cls(data=raw_data)

    def get_price(self, ticker: str, date: pd.Timestamp, price_type='Close') -> float | None:
        try:
            return self.data[ticker].loc[date, price_type]
        except KeyError:
            return None

    def get_series(self, ticker: str, price_type='Close') -> pd.Series:
        return self.data[ticker][price_type]

    def get_available_symbols(self) -> list:
        return list(self.data.keys())

    def get_history(self, ticker: str, end_date: pd.Timestamp, lookback: int) -> pd.DataFrame:
        """
        Return historical price data for a ticker ending on `end_date` and going back `lookback` days.
        """
        if ticker not in self.data:
            raise ValueError(f"ticker {ticker} not found in market data.")

        df = self.data[ticker]
        start_date = end_date - pd.Timedelta(days=lookback)
        return df.loc[start_date:end_date].copy()

    def get_all_data(self) -> Dict[str, pd.DataFrame]:
        return self.data
