import yfinance as yf
import pandas as pd


def load_price_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Load historical OHLCV data for a given symbol and date range.
    """
    df = yf.download(symbol, start=start_date, end=end_date)
    if df.empty or 'Close' not in df.columns:
        raise ValueError(f"No data returned for {symbol} in range {start_date} to {end_date}.")

    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    df.dropna(inplace=True)
    return df
