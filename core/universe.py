"""Tradable universes — the set of names a strategy is allowed to hold, over time.

The unit of an honest backtest is a *rule over a universe*, not a strategy on a hand-picked
ticker. A :class:`Universe` supplies the candidate tickers, a point-in-time **membership mask**
(was this name a member on this date), and a static ``meta`` table (sector, …).

The shipped :class:`SP500` is **survivorship-biased**: it uses *today's* constituents with an
all-``True`` membership mask. That bias is real and must be stamped on any report built from it
(see ``stamp``). A historical-membership feed later fills the same mask with real values, and no
strategy changes — they already read ``ctx.members``.
"""
import os
from abc import ABC, abstractmethod

import pandas as pd

_SP500_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sp500.csv")


def _normalize(symbol: str) -> str:
    """Wikipedia/exchange symbol → yahoo convention (e.g. ``BRK.B`` → ``BRK-B``)."""
    return symbol.strip().upper().replace(".", "-")


class Universe(ABC):
    name: str
    biased: bool = False

    @abstractmethod
    def tickers(self) -> list[str]:
        ...

    def membership(self, dates: pd.DatetimeIndex, tickers: list[str]) -> pd.DataFrame:
        """Boolean ``dates × tickers`` mask. Default: all-``True`` (labeled survivorship-biased)."""
        return pd.DataFrame(True, index=dates, columns=tickers)

    def meta(self) -> pd.DataFrame:
        """Static per-ticker attributes (sector, industry, …); empty by default."""
        return pd.DataFrame(index=self.tickers())

    def stamp(self) -> str | None:
        """A one-line bias caveat for reports, or ``None`` if the universe is unbiased."""
        if self.biased:
            return f"universe '{self.name}' is survivorship-biased (today's members, all-in mask) — indicative only"
        return None


class ListUniverse(Universe):
    """An explicit, fixed list of tickers (e.g. from the CLI ``--tickers``)."""

    name = "list"

    def __init__(self, tickers: list[str]):
        if not tickers:
            raise ValueError("ListUniverse needs at least one ticker")
        self._tickers = [_normalize(t) for t in tickers]

    def tickers(self) -> list[str]:
        return list(self._tickers)


class SP500(Universe):
    """S&P 500 constituents read from a local CSV snapshot (``data/sp500.csv``).

    Paste the membership table from Wikipedia into that file (any delimiter; needs a ``Symbol``
    column, optionally ``GICS Sector`` / ``GICS Sub-Industry``). A committed file is fully
    deterministic — a backtest re-derives identically and you refresh the list deliberately.
    Members are all-``True``, so this is **survivorship-biased**; ``stamp()`` flags it.
    """

    name = "sp500"
    biased = True

    def __init__(self, limit: int | None = None, path: str | None = None):
        self._limit = limit
        self._path = path or _SP500_FILE

    def _table(self) -> pd.DataFrame:
        if not os.path.exists(self._path):
            raise RuntimeError(
                f"S&P 500 snapshot not found at {self._path}. Paste the constituents table "
                f"(e.g. from Wikipedia) into that CSV — it needs a 'Symbol' column."
            )
        raw = pd.read_csv(self._path, sep=None, engine="python")
        cols = {c.lower().strip(): c for c in raw.columns}
        symbol_col = next((cols[k] for k in ("symbol", "ticker") if k in cols), None)
        if symbol_col is None:
            raise RuntimeError(f"{self._path} needs a 'Symbol' (or 'Ticker') column; found {list(raw.columns)}")

        table = pd.DataFrame({"ticker": raw[symbol_col].map(_normalize)})
        if "gics sector" in cols:
            table["sector"] = raw[cols["gics sector"]].to_numpy()
        if "gics sub-industry" in cols:
            table["industry"] = raw[cols["gics sub-industry"]].to_numpy()
        table = table.dropna(subset=["ticker"]).set_index("ticker").sort_index()

        if self._limit is not None:
            table = table.iloc[: self._limit]
        return table

    def tickers(self) -> list[str]:
        return list(self._table().index)

    def meta(self) -> pd.DataFrame:
        return self._table()


_UNIVERSES = {"sp500": SP500}


def create(name: str, **kwargs) -> Universe:
    if name not in _UNIVERSES:
        raise ValueError(f"Unknown universe '{name}'. Available: {sorted(_UNIVERSES)}")
    return _UNIVERSES[name](**kwargs)


def available() -> list[str]:
    return sorted(_UNIVERSES)
