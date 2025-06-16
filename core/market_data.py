# core/market_data.py
import pandas as pd
from typing import Dict, Any, List

from core.data_loader import DataIngestionManager


class MarketData:
    REQUIRED_COLUMNS = ['Open', 'High', 'Low', 'Close', 'Volume']

    def __init__(self, ingestion_manager: DataIngestionManager, simulation_start_date: str = None):
        self._ingestion_manager = ingestion_manager
        self.data: Dict[str, pd.DataFrame] | None = None
        self._simulation_start_date = pd.to_datetime(simulation_start_date)

    def _validate_all_data(self):
        for ticker, df in self.data.items():
            if not isinstance(df, pd.DataFrame):
                raise TypeError(f"Data for {ticker} must be a DataFrame, got {type(df)}")
            if not isinstance(df.index, pd.DatetimeIndex):
                raise ValueError(f"{ticker} DataFrame index must be a DatetimeIndex")
            missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                raise ValueError(f"{ticker} is missing required columns: {missing_cols}")

    def _clean_and_align_data(self):
        """
        Ensure all DataFrames have the required columns and share a common index
        :return:
        """
        common_index = None
        for ticker, df in self.data.items():
            # Filter DataFrame to include only REQUIRED_COLUMNS
            self.data[ticker] = df[self.REQUIRED_COLUMNS].copy()
            # Update common_index to the intersection of all DataFrame indices
            common_index = df.index if common_index is None else common_index.intersection(df.index)
            common_index = common_index.sort_values()

        if common_index.empty:
            raise ValueError("No common dates found across all tickers. Please check the date range and data availability.")
        if common_index is None:
            raise ValueError("No data available for the specified tickers and date range.")
        if not common_index.is_monotonic_increasing:
            raise ValueError("Common index dates are not in increasing order. Please check the data integrity.")

        # Align all DataFrames to the common index
        self._dates = common_index
        for ticker in self.data.keys():
            self.data[ticker] = self.data[ticker].reindex(common_index)

    def get_market_data(self,
                        tickers: List[str],
                        start_date: str,
                        end_date: str) -> None:
        """
        Create MarketData by fetching from a DataIngestionManager.
        """
        tickers = [t.strip().upper() for t in tickers]
        raw_data: Dict[str, pd.DataFrame] = self._ingestion_manager.get_data(tickers, start_date, end_date)

        # Populate and validate the raw data
        self.data = raw_data
        self._validate_all_data()
        self._clean_and_align_data()

    def get_price(self, ticker: str | list[str], date: pd.Timestamp, price_type='Close') -> float | dict[str, float] | None:
        ticker_list = []
        if isinstance(ticker, str):
            ticker_list = [tick.strip().upper() for tick in ticker.split(",")]
        elif isinstance(ticker, list):
            ticker_list = ticker

        price = {}
        try:
            for tick in ticker_list:
                price[tick] = self.data[tick].loc[date, price_type]
            return price
        except KeyError:
            return None

    def get_series(self, ticker: str, price_type='Close') -> pd.Series:
        return self.data[ticker][price_type]

    def get_available_symbols(self) -> list:
        return list(self.data.keys())

    def get_history(self, ticker_list: List[str], end_date: pd.Timestamp, lookback: int) -> Dict[str, pd.DataFrame]:
        """
        Return historical price data for a ticker ending on `end_date` and going back `lookback` days.
        """
        historical_data = {}
        for ticker in ticker_list:
            if ticker not in self.data:
                raise ValueError(f"ticker {ticker} not found in market data.")
            if end_date not in self.data[ticker].index:
                raise ValueError(f"end_date {end_date} not found in market data for ticker {ticker}.")
            if lookback < 0:
                raise ValueError("lookback must be a positive integer.")
            if lookback > len(self.data[ticker]):
                raise ValueError(f"lookback {lookback} exceeds available data length for ticker {ticker}.")
            # Calculate start date based on lookback period
            if lookback == 0:
                start_date = end_date
            else:
                end_date = pd.to_datetime(end_date)
                start_date = end_date - pd.Timedelta(days=lookback)
            if ticker not in historical_data:
                historical_data[ticker] = self.data[ticker].loc[start_date:end_date].copy()
        return historical_data

    def get_all_data(self) -> Dict[str, pd.DataFrame]:
        return self.data

    @property
    def dates(self) -> pd.DatetimeIndex:
        """
        Returns the common index of all DataFrames from the simulation start date onwards.
        Note: This method returns dates from the 'simulation' start date and not the data's start date (which includes the strategy lookback).
        """
        if self.data is None or not self.data:
            raise ValueError("Market data has not been loaded yet.")

        if self._simulation_start_date is None:
            return self._dates

        # Filter dates to include only those on or after the simulation start date
        return self._dates[self._dates >= self._simulation_start_date]