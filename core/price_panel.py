import pandas as pd


def to_price_panel(data: dict[str, pd.DataFrame], field: str = "Close", how: str = "inner") -> pd.DataFrame:
    """Flatten the per-ticker OHLCV dict from ``DataIngestionManager.get_data`` into a
    price panel for ``bt``: columns = tickers, rows = dates.

    yfinance returns auto-adjusted prices, so ``Close`` is the total-return series ``bt``
    should trade on. The panel is made tz-naive (``bt`` requires a naive DatetimeIndex) and
    sorted. ``how`` controls alignment across tickers:

    - ``"inner"`` (default): keep only dates present for *every* ticker (no NaN). Right for a
      single name or a small, fully-overlapping list.
    - ``"outer"``: union of all dates, keeping NaN where a name has no bar (it listed later,
      delisted, or missed a day). Right for a universe with staggered histories — the caller
      decides how to treat the gaps. Fully-empty dates are dropped.

    Args:
        data: ``{ticker: OHLCV DataFrame}`` with a tz-aware DatetimeIndex.
        field: OHLCV column to extract. Defaults to ``"Close"``.
        how: ``"inner"`` or ``"outer"`` alignment across tickers.

    Returns:
        A dates x tickers DataFrame of prices (no NaN for ``inner``; NaN-where-absent for ``outer``).
    """
    if not data:
        raise ValueError("No price data provided")
    if how not in ("inner", "outer"):
        raise ValueError(f"how must be 'inner' or 'outer', got {how!r}")

    columns = {}
    for ticker, df in data.items():
        if field not in df.columns:
            raise ValueError(f"'{field}' column missing for {ticker}")
        series = df[field].copy()
        if series.index.tz is not None:
            series.index = series.index.tz_localize(None)
        columns[ticker] = series

    panel = pd.DataFrame(columns).sort_index()
    panel = panel.dropna(how="all") if how == "outer" else panel.dropna(how="any")
    if panel.empty:
        raise ValueError("Price panel is empty after aligning tickers")
    return panel
