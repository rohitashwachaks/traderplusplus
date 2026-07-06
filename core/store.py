"""Canonical local price store — one additive parquet dataset, incrementally grown.

The MD5 request cache stores a copy per *(ticker, date-range)* request, so every new backtest
window refetches from the network and duplicates data. This store is the fix: **one file per
ticker** (`data_store/prices/{ticker}.parquet`, long OHLCV) plus a coverage index recording the
calendar window each ticker already holds. `ensure()` fetches only the *gap* between what is
stored and what a run needs, and appends. Re-running any backtest downloads nothing.

Daily bars only — intraday is out of scope for this platform and stays on the legacy path.
One vendor per ticker: mixing sources inside one series would let two runs silently disagree,
so a source change is an explicit error until the ticker is re-ingested.
"""
import json
import logging
import os
from datetime import date, timedelta
from typing import Callable

import pandas as pd

from utils.config import DATA_STORE

log = logging.getLogger("traderplusplus")

_OHLCV = ["Open", "High", "Low", "Close", "Volume"]

Fetcher = Callable[[str, str, str], pd.DataFrame]
"""(ticker, start, end) → OHLCV frame with a DatetimeIndex."""


def _default_fetcher(source: str) -> Fetcher:
    from core.data_loader import _fetch_data

    def fetch(ticker: str, start: str, end: str) -> pd.DataFrame:
        return _fetch_data(ticker, start, end, "1d", source)

    return fetch


def _normalize(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """As-fetched frame → store schema: tz-naive daily index, OHLCV columns, no all-NaN rows."""
    if df.empty:
        return pd.DataFrame(columns=_OHLCV, index=pd.DatetimeIndex([], name="date"))
    missing = [c for c in _OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"{ticker}: fetched frame is missing {missing} — cannot ingest")
    out = df[_OHLCV].copy()
    idx = pd.to_datetime(out.index)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    out.index = idx.normalize()
    out.index.name = "date"
    return out.dropna(how="all").sort_index()


class PriceStore:
    """Additive per-ticker parquet store with gap-only fetching.

    ``coverage.json`` records, per ticker, the **calendar window already ingested** (not just
    the bar dates — so a weekend-only "gap" never triggers a refetch) plus the vendor and fetch
    time. When a requested window reaches into today, the recorded coverage is capped at
    yesterday so a possibly-partial live bar is always refreshed on the next run.
    """

    def __init__(self, root: str | None = None, fetcher: Fetcher | None = None):
        self.root = root or DATA_STORE
        self._prices_dir = os.path.join(self.root, "prices")
        self._coverage_path = os.path.join(self.root, "coverage.json")
        self._fetcher = fetcher

    # -- coverage ---------------------------------------------------------------------------

    def coverage(self) -> dict[str, dict]:
        if not os.path.exists(self._coverage_path):
            return {}
        with open(self._coverage_path) as fh:
            return json.load(fh)

    def _write_coverage(self, cov: dict[str, dict]) -> None:
        os.makedirs(self.root, exist_ok=True)
        tmp = self._coverage_path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(cov, fh, indent=0, sort_keys=True)
        os.replace(tmp, self._coverage_path)

    def _path(self, ticker: str) -> str:
        return os.path.join(self._prices_dir, f"{ticker}.parquet")

    # -- ingest -----------------------------------------------------------------------------

    def ingest(self, ticker: str, df: pd.DataFrame, *, source: str,
               start: str, end: str) -> None:
        """Additively merge ``df`` into the ticker's series and extend its coverage window.

        Overlapping dates are resolved in favour of the **new** data (adjusted prices are
        retroactively restated by splits/dividends, so fresher is truer). Writes are
        atomic (tmp + rename), so a crash never leaves a half-written series.
        """
        new = _normalize(df, ticker)
        path = self._path(ticker)
        if os.path.exists(path):
            old = pd.read_parquet(path)
            merged = pd.concat([old, new])
            merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        else:
            merged = new
        os.makedirs(self._prices_dir, exist_ok=True)
        tmp = path + ".tmp"
        merged.to_parquet(tmp)
        os.replace(tmp, path)

        cov = self.coverage()
        entry = cov.get(ticker)
        covered_end = min(pd.Timestamp(end).date(), date.today() - timedelta(days=1))
        new_start = pd.Timestamp(start).date()
        if entry:
            new_start = min(new_start, pd.Timestamp(entry["start"]).date())
            covered_end = max(covered_end, pd.Timestamp(entry["end"]).date())
        cov[ticker] = {
            "start": str(new_start),
            "end": str(covered_end),
            "source": source,
            "fetched_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        }
        self._write_coverage(cov)

    def forget(self, ticker: str) -> None:
        """Drop a ticker's series and coverage so the next ``ensure`` refetches from scratch."""
        cov = self.coverage()
        cov.pop(ticker, None)
        self._write_coverage(cov)
        path = self._path(ticker)
        if os.path.exists(path):
            os.remove(path)

    # -- the main entry points ---------------------------------------------------------------

    def ensure(self, tickers: list[str], start: str, end: str, *, source: str = "yahoo") -> None:
        """Fetch and ingest only the parts of ``[start, end]`` not already stored."""
        fetch = self._fetcher or _default_fetcher(source)
        cov = self.coverage()
        for ticker in tickers:
            entry = cov.get(ticker)
            if entry and entry["source"] != source:
                raise ValueError(
                    f"{ticker} is stored from '{entry['source']}' but '{source}' was requested. "
                    f"One vendor per ticker — call PriceStore().forget('{ticker}') to switch."
                )
            for gap_start, gap_end in self._gaps(entry, start, end):
                try:
                    fetched = fetch(ticker, gap_start, gap_end)
                except ValueError as exc:
                    # A vendor returning nothing for a window (not yet listed, delisted) is a
                    # real, expected outcome — record the window so we don't refetch forever.
                    log.warning("%s: no data for [%s, %s] (%s); recording empty coverage",
                                ticker, gap_start, gap_end, exc)
                    fetched = pd.DataFrame(columns=_OHLCV)
                self.ingest(ticker, fetched, source=source, start=gap_start, end=gap_end)

    @staticmethod
    def _gaps(entry: dict | None, start: str, end: str) -> list[tuple[str, str]]:
        """Calendar windows inside ``[start, end]`` not yet covered by ``entry``."""
        req_start, req_end = pd.Timestamp(start).date(), pd.Timestamp(end).date()
        if entry is None:
            return [(str(req_start), str(req_end))]
        cov_start, cov_end = pd.Timestamp(entry["start"]).date(), pd.Timestamp(entry["end"]).date()
        gaps = []
        if req_start < cov_start:
            gaps.append((str(req_start), str(cov_start - timedelta(days=1))))
        if req_end > cov_end:
            gaps.append((str(cov_end + timedelta(days=1)), str(req_end)))
        return gaps

    def load(self, tickers: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
        """Read stored OHLCV frames sliced to ``[start, end]``.

        Raises for a ticker never ingested (run ``ensure`` first); a ticker that *was*
        ingested but has no bars in the window comes back empty — the panel layer surfaces
        those as dropped names, loudly.
        """
        out: dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            path = self._path(ticker)
            if not os.path.exists(path):
                raise KeyError(f"{ticker} is not in the price store — call ensure() first")
            df = pd.read_parquet(path)
            out[ticker] = df.loc[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))]
        return out
