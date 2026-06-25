"""The single data object a strategy sees.

A :class:`DataContext` bundles several aligned ``dates × tickers`` panels (price, membership,
and any feature like ``"pe"``) plus a static per-ticker ``meta`` table. Strategies read
everything through this one object and never learn where a panel came from, so new data
sources (see :mod:`core.sources`) can be added or swapped without touching any strategy.
"""
from dataclasses import dataclass

import pandas as pd

from core import sources as _sources


@dataclass(frozen=True)
class DataContext:
    """Aligned data panels + static metadata, addressed by name.

    ``panels`` always contains at least ``"price"`` and ``"members"``; richer contexts add
    feature panels (e.g. ``"pe"``) under their own names. Every panel shares the same
    ``dates × tickers`` grid, so strategies do pure column-wise work and the no-look-ahead /
    point-in-time guarantees live in how each panel was *built*, not in the strategy.
    """

    panels: dict[str, pd.DataFrame]
    meta: pd.DataFrame

    @property
    def price(self) -> pd.DataFrame:
        return self.panel("price")

    @property
    def members(self) -> pd.DataFrame:
        """Boolean ``dates × tickers`` mask: was this name in the universe on this date."""
        return self.panel("members")

    def panel(self, name: str) -> pd.DataFrame:
        if name not in self.panels:
            raise KeyError(f"Panel '{name}' not in context. Have: {sorted(self.panels)}")
        return self.panels[name]

    def has(self, name: str) -> bool:
        return name in self.panels

    def fundamental(self, name: str) -> pd.DataFrame:
        """Read a point-in-time feature panel (alias of :meth:`panel`, reads better in strategies)."""
        return self.panel(name)

    @classmethod
    def from_prices(
        cls,
        price: pd.DataFrame,
        *,
        members: pd.DataFrame | None = None,
        meta: pd.DataFrame | None = None,
    ) -> "DataContext":
        """Build a price-only context (members default to all-in). For tests and simple runs."""
        if members is None:
            members = pd.DataFrame(True, index=price.index, columns=price.columns)
        if meta is None:
            meta = pd.DataFrame(index=price.columns)
        return cls(panels={"price": price, "members": members}, meta=meta)


def build_context(
    universe,
    start: str,
    end: str,
    *,
    panels: tuple[str, ...] = ("price",),
    **opts,
) -> DataContext:
    """Assemble a :class:`DataContext` for ``universe`` over ``[start, end]``.

    Each requested panel is pulled from its registered source (:mod:`core.sources`), reindexed
    onto the price calendar, and bundled with the universe's membership mask and ``meta``.
    ``"price"`` must be among ``panels`` — it defines the trading calendar everything aligns to.

    Args:
        universe: a :class:`~core.universe.Universe` (provides tickers, membership, meta).
        start, end: date window (YYYY-MM-DD).
        panels: panel names to load; ``"price"`` is required and always the calendar.
        **opts: source-specific options (e.g. ``source="yahoo"``, ``interval="1d"``).
    """
    if "price" not in panels:
        raise ValueError("build_context requires the 'price' panel (it sets the calendar)")

    tickers = universe.tickers()
    loaded = {name: _sources.get_source(name).load(tickers, start, end, **opts) for name in panels}

    calendar = loaded["price"].index
    columns = list(loaded["price"].columns)
    aligned = {name: panel.reindex(calendar) for name, panel in loaded.items()}
    aligned["members"] = universe.membership(calendar, columns)
    meta = universe.meta().reindex(columns)
    return DataContext(panels=aligned, meta=meta)
