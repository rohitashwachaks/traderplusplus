import logging

import pandas as pd

log = logging.getLogger("traderplusplus")


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
    return _validated(panel)


def _validated(panel: pd.DataFrame) -> pd.DataFrame:
    """Data-quality gate: corrupt structure raises; suspect values are nulled *loudly*.

    A data error that slips through here masquerades as alpha downstream, so nothing is
    silently tolerated: duplicate dates are structural corruption (raise); non-positive
    prices are vendor glitches (set to NaN with a named warning — the membership mask then
    keeps the name untradable on those days); extreme one-day moves are flagged for a human.
    """
    if panel.index.duplicated().any():
        dupes = panel.index[panel.index.duplicated()].unique()
        raise ValueError(f"Price panel has duplicated dates (corrupt input): {list(dupes[:5])}")

    bad = (panel <= 0)
    if bad.any().any():
        counts = bad.sum()
        offenders = {t: int(n) for t, n in counts[counts > 0].items()}
        log.warning("Non-positive prices nulled (vendor data error): %s", offenders)
        panel = panel.where(~bad)

    jumps = panel.pct_change().abs() > 0.5
    if jumps.any().any():
        counts = jumps.sum()
        offenders = {t: int(n) for t, n in counts[counts > 0].items()}
        log.warning(">50%% one-day moves — verify these are real, not data errors: %s", offenders)
    return panel
