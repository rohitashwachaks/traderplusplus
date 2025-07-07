import re
from datetime import timedelta

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


def period_to_timedelta(period: str) -> timedelta:
    match = re.match(r"(\d+)([a-zA-Z]+)", str(period))
    if not match:
        raise ValueError(f"Invalid period format: {period}")
    value, unit = int(match.group(1)), match.group(2).lower()
    if unit in ["d", "day", "days"]:
        return timedelta(days=value)
    elif unit in ["w", "week", "weeks"]:
        return timedelta(weeks=value)
    elif unit in ["mo", "month", "months"]:
        return timedelta(weeks=4 * value)
    elif unit in ["y", "yr", "year", "years"]:
        return timedelta(weeks=52 * value)
    elif unit in ["m", "min", "mins", "minute", "minutes"]:
        return timedelta(minutes=value)
    else:
        raise ValueError(f"Unsupported period unit: {unit}")


def split_period(period: str) -> timedelta:
    match = re.match(r"(\d+)([a-zA-Z]+)", str(period))
    if not match:
        raise ValueError(f"Invalid period format: {period}")
    value, unit = int(match.group(1)), match.group(2).lower()
    if unit in ["w", "week", "weeks"]:
        timespan = "week"
    elif unit in ["mo", "month", "months"]:
        timespan = "month"
    elif unit in ["y", "yr", "year", "years"]:
        timespan = "year"
    elif unit in ["m", "min", "mins", "minute", "minutes"]:
        timespan = "minute"
    elif unit in ["h", "hr", "hour", "hours", "hrs"]:
        timespan = "hour"
    else:
        timespan = "day"

    return value, timespan
