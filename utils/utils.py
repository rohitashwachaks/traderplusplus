import re
from datetime import timedelta


def clean_ticker(ticker: str) -> str:
    """Normalize a ticker to yahoo convention (upper-case, dots → dashes). No network.

    Validity is proven by the data fetch itself — a bad symbol fails loudly there — so this
    only rejects strings that can't be a symbol at all.
    """
    if not isinstance(ticker, str):
        raise ValueError("Ticker must be a string")
    ticker = ticker.strip().upper().replace(".", "-")
    if not re.fullmatch(r"[A-Z0-9-]{1,10}", ticker):
        raise ValueError(f"Invalid ticker: {ticker!r}")
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
