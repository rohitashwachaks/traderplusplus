import yfinance as yf


def fetch_yahoo_data(ticker: str, start_date: str, end_date: str):
    data = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False, threads=False)
    return data
