import pandas as pd
import yfinance as yf


def fetch_yahoo_data(ticker: str, start_date: str, end_date: str, interval: str = "1d") -> pd.DataFrame:
    """OHLCV from Yahoo with ``auto_adjust=True`` pinned **explicitly**.

    Adjusted prices make ``Close`` a total-return series (splits and dividends folded in),
    which is what the backtest and the benchmark must both trade on — leaving the flag to
    yfinance's default would let that semantic drift under us.
    """
    if interval.endswith("m"):
        data = yf.download(ticker, end=end_date, interval=interval, period='1wk',
                           auto_adjust=True, multi_level_index=False, threads=False)
    else:
        data = yf.download(ticker, start=start_date, end=end_date,
                           auto_adjust=True, multi_level_index=False, threads=False)

    return data
