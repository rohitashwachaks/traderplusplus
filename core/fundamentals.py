"""Point-in-time fundamentals — the as-of fundamentals panels behind the context.

The one rule that keeps a fundamental backtest honest: a value is placed on the date it became
**public** (its ``filed`` date), never the period it describes, and restatements are ignored in
favour of the **as-first-filed** number. Here that produces a sparse panel indexed by filing
date; ``build_context`` forward-fills it onto the trading calendar (past-only → no look-ahead).
"""
import logging

import pandas as pd

from core.sources import PanelSource, register_source
from data_ingestion.edgar_fetcher import cik_map, fetch_concept

log = logging.getLogger("traderplusplus")

_ANNUAL_MIN_DAYS = 300  # a full fiscal year, to exclude quarterly / YTD EPS entries


def annual_eps_series(records: list[dict]) -> pd.Series:
    """As-first-filed **annual** diluted EPS, indexed by filing date.

    From the raw ``companyconcept`` datapoints, keep only full-year periods (so quarterly and
    9-month YTD entries drop out), then for each fiscal year keep the **earliest** filing — the
    number as it was first reported, not a later restatement. The resulting series is indexed by
    ``filed`` date so the value only becomes visible once it was public.

    Args:
        records: ``{start, end, val, filed, ...}`` dicts from :func:`fetch_concept`.

    Returns:
        EPS indexed by filing date (ascending), one point per fiscal year.
    """
    first_by_period: dict[pd.Timestamp, tuple[pd.Timestamp, float]] = {}
    annual = []
    for r in records:
        start, end, filed, val = r.get("start"), r.get("end"), r.get("filed"), r.get("val")
        if start is None or end is None or filed is None or val is None:
            continue
        start, end, filed = pd.Timestamp(start), pd.Timestamp(end), pd.Timestamp(filed)
        if (end - start).days <= _ANNUAL_MIN_DAYS:
            continue  # not a full-year period
        annual.append((end, filed, float(val)))

    for end, filed, val in sorted(annual, key=lambda row: row[1]):  # earliest filing wins
        first_by_period.setdefault(end, (filed, val))

    if not first_by_period:
        return pd.Series(dtype=float)

    points = sorted(first_by_period.values())  # by filed date
    series = pd.Series({filed: val for filed, val in points})
    series.index = pd.to_datetime(series.index)
    return series.groupby(level=0).last().sort_index()


class EpsSource(PanelSource):
    """Annual diluted EPS per ticker, indexed by filing date (sparse, point-in-time).

    ``build_context`` forward-fills this onto the trading calendar, so on any date a strategy
    sees the most recent EPS that had actually been filed by then.
    """

    name = "eps"

    def load(self, tickers: list[str], start: str, end: str, **opts) -> pd.DataFrame:
        ciks = cik_map()
        columns: dict[str, pd.Series] = {}
        for ticker in tickers:
            cik = ciks.get(ticker)
            if cik is None:
                log.warning("no EDGAR CIK for %s; no EPS", ticker)
                continue
            series = annual_eps_series(fetch_concept(cik, "EarningsPerShareDiluted"))
            if not series.empty:
                columns[ticker] = series
        if not columns:
            return pd.DataFrame(columns=tickers)
        return pd.DataFrame(columns).sort_index()


register_source(EpsSource())
