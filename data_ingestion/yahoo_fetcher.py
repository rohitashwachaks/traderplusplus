import pandas as pd
import yfinance as yf


def fetch_yahoo_data(ticker: str, start_date: str, end_date: str, interval: str = "1d") -> pd.DataFrame:
    if interval.endswith("m"):
        data = yf.download(ticker, end=end_date, interval=interval, period='1wk', multi_level_index=False, threads=False)
    else:
        data = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False, threads=False)

    return data
