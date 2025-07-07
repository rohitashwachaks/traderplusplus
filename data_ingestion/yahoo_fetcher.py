import pandas as pd
import yfinance as yf


def fetch_yahoo_data(ticker: str, start_date: str, end_date: str, interval: str = "1d") -> pd.DataFrame:
    data = yf.download(ticker, start=start_date, end=end_date, interval=interval, multi_level_index=False, threads=False)
    return data
