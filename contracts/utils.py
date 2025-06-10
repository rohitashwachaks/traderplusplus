import yfinance as yf

# TODO: Add support for multiple data sources in the future. Perhaps move to DataIngestionManager?


def clean_ticker(ticker):
    """    Validate and format a ticker string.
    Args:
        ticker (str): Ticker symbol to validate.
    Returns:
        str: Validated and formatted ticker symbol.
    Raises:
        ValueError: If the ticker is invalid.
    """
    if not isinstance(ticker, str):
        raise ValueError("Ticker must be a string")
    ticker = ticker.strip().upper()
    if not ticker.isalpha() or len(ticker) < 1 or len(ticker) > 5:
        raise ValueError(f"Invalid ticker: {ticker}. Tickers must be 1-5 alphabetic characters.")
    # check if ticker is a valid stock symbol, on yahoo finance
    try:
        _ = yf.Ticker(ticker).info  # This will raise an error if ticker is invalid
    except Exception as e:
        raise ValueError(f"Invalid ticker: {ticker}. Error: {str(e)}")
    return ticker
