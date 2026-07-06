"""Pluggable data sources behind the :class:`~core.context.DataContext`.

Each source produces one named ``dates × tickers`` panel for a universe and date window and
registers under that panel name. Strategies never call a source directly — they read panels
through the ``DataContext`` — so a new source (e.g. EDGAR fundamentals) plugs in by
registering here, with no change to any strategy.
"""
from abc import ABC, abstractmethod

import pandas as pd

from core.data_loader import DataIngestionManager
from core.price_panel import to_price_panel

_SOURCES: dict[str, "PanelSource"] = {}


def register_source(source: "PanelSource") -> "PanelSource":
    """Register ``source`` under its ``name`` for lookup via :func:`get_source`."""
    _SOURCES[source.name] = source
    return source


def get_source(name: str) -> "PanelSource":
    if name not in _SOURCES:
        raise KeyError(f"No data source registered for panel '{name}'. Available: {sorted(_SOURCES)}")
    return _SOURCES[name]


def available_panels() -> list[str]:
    return sorted(_SOURCES)


class PanelSource(ABC):
    """Produces one named ``dates × tickers`` panel for a universe + window.

    Subclasses set ``name`` (the panel they serve) and implement :meth:`load`. Source-specific
    options (data vendor, bar interval, …) travel as ``**opts`` so the registry can stay
    uniform across very different sources.
    """

    name: str

    @abstractmethod
    def load(self, tickers: list[str], start: str, end: str, **opts) -> pd.DataFrame:
        """Return a ``dates × tickers`` panel for ``tickers`` over ``[start, end]``."""
        ...


class _OhlcvFieldSource(PanelSource):
    """One OHLCV field as a panel, served from the canonical :class:`~core.store.PriceStore`.

    Daily bars go through the store (gap-only fetching, one additive copy per ticker); any
    other interval falls back to the legacy per-request cache, since the store is
    deliberately daily-only.
    """

    field: str

    def load(self, tickers: list[str], start: str, end: str, **opts) -> pd.DataFrame:
        source = opts.get("source", "yahoo")
        interval = opts.get("interval", "1d")
        how = opts.get("how", "inner")
        if interval != "1d":
            data = DataIngestionManager(source=source).get_data(
                tickers, end_date=end, start_date=start, interval=interval
            )
            return to_price_panel(data, field=self.field, how=how)

        from core.store import PriceStore

        store = PriceStore()
        store.ensure(tickers, start, end, source=source)
        return to_price_panel(store.load(tickers, start, end), field=self.field, how=how)


class PriceSource(_OhlcvFieldSource):
    name = "price"
    field = "Close"


class HighSource(_OhlcvFieldSource):
    """Intraday highs — lets guardrails trail a stop off the real peak, not just closes."""

    name = "high"
    field = "High"


class LowSource(_OhlcvFieldSource):
    """Intraday lows — lets guardrails detect a stop being touched, not just crossed at close."""

    name = "low"
    field = "Low"


register_source(PriceSource())
register_source(HighSource())
register_source(LowSource())
