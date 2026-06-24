import pandas as pd


def to_price_panel(data: dict[str, pd.DataFrame], field: str = "Close") -> pd.DataFrame:
    """Flatten the per-ticker OHLCV dict from ``DataIngestionManager.get_data`` into a
    price panel for ``bt``: columns = tickers, rows = dates.

    yfinance returns auto-adjusted prices, so ``Close`` is the total-return series ``bt``
    should trade on. The panel is made tz-naive (``bt`` requires a naive DatetimeIndex),
    inner-joined on dates common to every ticker, and sorted.

    Args:
        data: ``{ticker: OHLCV DataFrame}`` with a tz-aware DatetimeIndex.
        field: OHLCV column to extract. Defaults to ``"Close"``.

    Returns:
        A dates x tickers DataFrame of prices with no missing values.
    """
    if not data:
        raise ValueError("No price data provided")

    columns = {}
    for ticker, df in data.items():
        if field not in df.columns:
            raise ValueError(f"'{field}' column missing for {ticker}")
        series = df[field].copy()
        if series.index.tz is not None:
            series.index = series.index.tz_localize(None)
        columns[ticker] = series

    panel = pd.DataFrame(columns).sort_index().dropna(how="any")
    if panel.empty:
        raise ValueError("Price panel is empty after aligning tickers on common dates")
    return panel
