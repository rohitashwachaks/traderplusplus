import yfinance as yf


def fetch_yahoo_data(symbol: str, start_date: str, end_date: str):
    data = yf.download(symbol, start=start_date, end=end_date, multi_level_index=False)
    return data
