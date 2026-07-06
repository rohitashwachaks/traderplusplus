"""Point-in-time fundamentals — the as-of fundamentals panels behind the context.

The one rule that keeps a fundamental backtest honest: a value is placed on the date it became
**public** (its ``filed`` date), never the period it describes, and restatements are ignored in
favour of the **as-first-filed** number. Here that produces a sparse panel indexed by filing
date; ``build_context`` forward-fills it onto the trading calendar (past-only → no look-ahead).
"""
import logging

import pandas as pd

from core.sources import PanelSource, register_source
from data_ingestion.edgar_fetcher import cik_map, fetch_concept, fetch_submissions

log = logging.getLogger("traderplusplus")

_ANNUAL_MIN_DAYS = 300   # a full fiscal year, to exclude quarterly / YTD EPS entries
_QUARTER_DAYS = (60, 120)  # a single quarter (excludes 6/9-month YTD periods)
_TTM_MAX_SPAN_DAYS = 320   # four *consecutive* quarter-ends span ~275 days; a gap breaks TTM


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
    rows = _parse(records)
    first = _first_filed(r for r in rows if (r[1] - r[0]).days > _ANNUAL_MIN_DAYS)
    if not first:
        return pd.Series(dtype=float)
    series = pd.Series({filed: val for filed, val in sorted(first.values())})
    return series.groupby(level=0).last().sort_index()


def _parse(records: list[dict]) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, float]]:
    """Raw datapoints → complete ``(start, end, filed, val)`` tuples."""
    out = []
    for r in records:
        start, end, filed, val = r.get("start"), r.get("end"), r.get("filed"), r.get("val")
        if start is None or end is None or filed is None or val is None or pd.isna(val):
            continue
        out.append((pd.Timestamp(start), pd.Timestamp(end), pd.Timestamp(filed), float(val)))
    return out


def _first_filed(rows) -> dict[pd.Timestamp, tuple[pd.Timestamp, float]]:
    """Per period-end, the earliest-filed value: ``{end: (filed, val)}`` — as-first-filed."""
    first: dict[pd.Timestamp, tuple[pd.Timestamp, float]] = {}
    for start, end, filed, val in sorted(rows, key=lambda r: r[2]):
        first.setdefault(end, (filed, val))
    return first


def ttm_eps_series(records: list[dict]) -> pd.Series:
    """As-first-filed **trailing-twelve-month** diluted EPS, indexed by filing date.

    Quarterly EPS accumulates as each 10-Q is filed; the never-filed Q4 is reconstructed from
    the 10-K as ``Q4 = FY − (Q1 + Q2 + Q3)`` and placed on the **10-K's** filing date — every
    input to that subtraction was public by then, so the placement is point-in-time. After
    each filing event, if the four most recent known quarter-ends are consecutive (span ≤
    ~320 days), their sum is the TTM as of that date. Quarter EPS is not perfectly additive
    when the share count moves within the year — an approximation carried by ``eps_ttm``, not
    hidden.
    """
    rows = _parse(records)
    quarters = _first_filed(r for r in rows if _QUARTER_DAYS[0] <= (r[1] - r[0]).days <= _QUARTER_DAYS[1])
    annuals = _first_filed(r for r in rows if (r[1] - r[0]).days > _ANNUAL_MIN_DAYS)
    annual_spans = {end: start for start, end, _, _ in rows if (end - start).days > _ANNUAL_MIN_DAYS}

    events = [(filed, end, val) for end, (filed, val) in quarters.items()]
    for fy_end, (fy_filed, fy_val) in annuals.items():
        fy_start = annual_spans[fy_end]
        interim = [end for end in quarters if fy_start < end < fy_end]
        if len(interim) != 3:
            continue  # can't reconstruct Q4 without exactly Q1–Q3 — skip this year, loudly PIT-safe
        q4 = fy_val - sum(quarters[end][1] for end in interim)
        events.append((fy_filed, fy_end, q4))

    known: dict[pd.Timestamp, float] = {}
    points: dict[pd.Timestamp, float] = {}
    for filed, q_end, val in sorted(events):
        known.setdefault(q_end, val)  # as-first-filed: never overwrite a quarter
        ends = sorted(known)[-4:]
        if len(ends) == 4 and (ends[-1] - ends[0]).days <= _TTM_MAX_SPAN_DAYS:
            points[filed] = sum(known[e] for e in ends)

    if not points:
        return pd.Series(dtype=float)
    series = pd.Series(points).sort_index()
    return series.groupby(level=0).last()


def instant_series(records: list[dict]) -> pd.Series:
    """Point-in-time series for *instant* facts (e.g. shares outstanding), indexed by filing.

    Each filing reports the value as of its cover date; a late-arriving amendment carrying an
    *older* as-of date must not regress the series, so only monotonically newer cover dates
    are kept.
    """
    rows = []
    for r in records:
        end, filed, val = r.get("end"), r.get("filed"), r.get("val")
        if end is None or filed is None or val is None or pd.isna(val):
            continue
        rows.append((pd.Timestamp(filed), pd.Timestamp(end), float(val)))

    points: dict[pd.Timestamp, float] = {}
    latest_end = pd.Timestamp.min
    for filed, end, val in sorted(rows):
        if end < latest_end:
            continue  # amendment with stale as-of data
        latest_end = end
        points[filed] = val
    if not points:
        return pd.Series(dtype=float)
    return pd.Series(points).sort_index()


def _eps_records(cik: str) -> list[dict]:
    """Diluted EPS datapoints, falling back to basic EPS when diluted was never tagged."""
    records = fetch_concept(cik, "EarningsPerShareDiluted")
    if not records:
        records = fetch_concept(cik, "EarningsPerShareBasic")
        if records:
            log.info("CIK %s: no diluted EPS tagged — using basic EPS", cik)
    return records


def _panel_of(tickers: list[str], build_series, what: str) -> pd.DataFrame:
    """One sparse filed-date-indexed column per ticker, via the CIK map."""
    ciks = cik_map()
    columns: dict[str, pd.Series] = {}
    for ticker in tickers:
        cik = ciks.get(ticker)
        if cik is None:
            log.warning("no EDGAR CIK for %s; no %s", ticker, what)
            continue
        series = build_series(cik)
        if not series.empty:
            columns[ticker] = series
    if not columns:
        return pd.DataFrame(columns=tickers)
    return pd.DataFrame(columns).sort_index()


def sic_meta(tickers: list[str]) -> pd.DataFrame:
    """Static SIC classification per ticker (``sic``, ``sic_description``) from EDGAR."""
    ciks = cik_map()
    rows = {}
    for ticker in tickers:
        cik = ciks.get(ticker)
        if cik is None:
            log.warning("no EDGAR CIK for %s; no SIC", ticker)
            continue
        payload = fetch_submissions(cik)
        rows[ticker] = {"sic": payload.get("sic"), "sic_description": payload.get("sicDescription")}
    return pd.DataFrame.from_dict(rows, orient="index").reindex(tickers)


class EpsSource(PanelSource):
    """Annual diluted EPS per ticker, indexed by filing date (sparse, point-in-time).

    ``build_context`` forward-fills this onto the trading calendar, so on any date a strategy
    sees the most recent EPS that had actually been filed by then.
    """

    name = "eps"

    def load(self, tickers: list[str], start: str, end: str, **opts) -> pd.DataFrame:
        return _panel_of(tickers, lambda cik: annual_eps_series(_eps_records(cik)), "EPS")


class TtmEpsSource(PanelSource):
    """Trailing-twelve-month diluted EPS (Q4 reconstructed from the 10-K), point-in-time.

    More responsive than the annual panel — a strategy chooses ``requires=("eps_ttm",)``
    explicitly, since the Q4 reconstruction is an approximation the annual number doesn't
    carry.
    """

    name = "eps_ttm"

    def load(self, tickers: list[str], start: str, end: str, **opts) -> pd.DataFrame:
        return _panel_of(tickers, lambda cik: ttm_eps_series(_eps_records(cik)), "TTM EPS")


class SharesSource(PanelSource):
    """Common shares outstanding (dei tag, from every 10-K/10-Q cover), point-in-time.

    Market cap is a one-liner on top: ``ctx.price * ctx.fundamental("shares")`` — both panels
    share the same calendar, so the product is the PIT market cap panel.
    """

    name = "shares"

    def load(self, tickers: list[str], start: str, end: str, **opts) -> pd.DataFrame:
        return _panel_of(
            tickers,
            lambda cik: instant_series(
                fetch_concept(cik, "EntityCommonStockSharesOutstanding", taxonomy="dei")),
            "shares outstanding",
        )


register_source(EpsSource())
register_source(TtmEpsSource())
register_source(SharesSource())
