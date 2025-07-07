import yfinance as yf

# TODO: Add support for multiple data sources in the future. Perhaps move to DataIngestionManager?


def clean_ticker(ticker):
    """    Validate and format a ticker string.
    Args:
        ticker (str): Ticker ticker to validate.
    Returns:
        str: Validated and formatted ticker ticker.
    Raises:
        ValueError: If the ticker is invalid.
    """
    if not isinstance(ticker, str):
        raise ValueError("Ticker must be a string")
    ticker = ticker.strip().upper()
    if not ticker.isalpha() or len(ticker) < 1 or len(ticker) > 5:
        raise ValueError(f"Invalid ticker: {ticker}. Tickers must be 1-5 alphabetic characters.")
    # check if ticker is a valid multi_asset ticker, on yahoo finance
    ticker_obj = yf.Ticker(ticker)

    # Option 1: Try fetching recent history (safe and reliable)
    hist = ticker_obj.history(period="1d")
    if hist.empty:
        raise ValueError(f"Invalid ticker: {ticker}. Ticker not found on Yahoo Finance.")
    return ticker
