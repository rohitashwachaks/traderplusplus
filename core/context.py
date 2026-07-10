"""The single data object a strategy sees.

A :class:`DataContext` bundles several aligned ``dates × tickers`` panels (price, membership,
and any feature like ``"pe"``) plus a static per-ticker ``meta`` table. Strategies read
everything through this one object and never learn where a panel came from, so new data
sources (see :mod:`core.sources`) can be added or swapped without touching any strategy.
"""
import logging
from dataclasses import dataclass

import pandas as pd

from core import sources as _sources

log = logging.getLogger("traderplusplus")


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

    def classification(self, by: str) -> pd.Series:
        """Static per-ticker group label (e.g. ``"sector"``, ``"industry"``, ``"sic2"``).

        Aligned to the price columns, so it drops straight into cross-sectional group ops
        (see :mod:`strategies.grouping`). Unlike a panel this is **static** — one label per
        name for all history — which is a labeled classification bias (sector drift is
        unmodeled), not a look-ahead within the day.
        """
        if by not in self.meta.columns:
            raise KeyError(
                f"No classification '{by}' in meta. Have: {sorted(self.meta.columns)}. "
                f"For a non-GICS universe, request SIC via build_context(classify=True)."
            )
        return self.meta[by].reindex(self.price.columns)

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
    join: str = "outer",
    classify: bool = False,
    **opts,
) -> DataContext:
    """Assemble a :class:`DataContext` for ``universe`` over ``[start, end]``.

    Each requested panel is pulled from its registered source (:mod:`core.sources`), reindexed
    onto the price calendar, and bundled with a membership mask and ``meta``. ``"price"`` must
    be among ``panels`` — it sets the trading calendar everything aligns to.

    Prices are outer-joined (``join="outer"``) so a universe with staggered listing/delisting
    histories keeps every name; columns with no data at all are dropped (logged). The
    membership mask is the universe's own membership **and** ``price.notna()`` — so a name is
    only ever held on dates it actually traded. That keeps the backtest honest: no holding a
    stock before it listed or after it delisted, even while the labeled-biased universe assumes
    today's members throughout.

    Args:
        universe: a :class:`~core.universe.Universe` (provides tickers, membership, meta).
        start, end: date window (YYYY-MM-DD).
        panels: panel names to load; ``"price"`` is required and always the calendar.
        join: price alignment across names — ``"outer"`` (universe-safe) or ``"inner"``.
        **opts: source-specific options (e.g. ``source="yahoo"``, ``interval="1d"``).
    """
    if "price" not in panels:
        raise ValueError("build_context requires the 'price' panel (it sets the calendar)")

    tickers = universe.tickers()
    loaded = {name: _sources.get_source(name).load(tickers, start, end, how=join, **opts) for name in panels}

    price = loaded["price"]
    empty = price.columns[price.isna().all()]
    if len(empty):
        log.warning("dropping %d names with no price data: %s", len(empty), list(empty))
        price = price.drop(columns=empty)
        loaded["price"] = price

    calendar = price.index
    columns = list(price.columns)
    aligned = {"price": price}
    for name, panel in loaded.items():
        if name == "price":
            continue
        # Point-in-time alignment: forward-fill each feature from its filing/availability date
        # onto the trading calendar. ffill only ever reaches back, so this stays no-look-ahead.
        idx = calendar.union(panel.index)
        aligned[name] = panel.reindex(index=idx, columns=columns).ffill().reindex(calendar)
    aligned["members"] = universe.membership(calendar, columns) & price.notna()
    meta = universe.meta().reindex(columns)
    if classify:
        meta = _with_sic(meta, columns)
    return DataContext(panels=aligned, meta=meta)


def _with_sic(meta: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Merge EDGAR SIC classification onto ``meta``: ``sic``, ``sic_description``, ``sic2``.

    SIC is the general (any-US-filer) taxonomy, from the single EDGAR source; ``sic2`` is the
    2-digit major group — coarse enough that sector-neutral ranking has names per bucket
    (raw 4-digit SIC is often one name). GICS columns from the universe CSV are left as-is.
    """
    from core.fundamentals import sic_meta

    sic = sic_meta(columns)
    sic["sic"] = sic["sic"].astype("string")
    sic["sic2"] = sic["sic"].str.zfill(4).str[:2]
    return meta.join(sic, how="left")
