import pandas as pd

import core.fundamentals  # noqa: F401  (registers the "eps" data source)
from core.context import DataContext
from strategies.base import TargetWeightStrategy, register


@register("ls_pe")
class LongShortPE(TargetWeightStrategy):
    """Dollar-neutral long/short on trailing P/E: long the cheapest names, short the richest.

    P/E = price / annual diluted EPS, with the EPS keyed to its **filing date** (point-in-time,
    see :mod:`core.fundamentals`) — so the rank on any day uses only earnings that were public
    then. Names with non-positive EPS are dropped (P/E is meaningless there). The book is only
    formed when at least ``2*n`` names have a valid P/E, so the long and short legs never
    overlap; weights are ``+1/n`` / ``-1/n`` and sum to ~0 (market-neutral → beta ≈ 0).
    """

    name = "ls_pe"
    requires = ("eps",)
    rebalance_freq = "M"
    reconstitution_freq = "M"

    def __init__(self, n: int = 5):
        if n < 1:
            raise ValueError("n must be >= 1")
        self.n = n

    def weights(self, ctx: DataContext) -> pd.DataFrame:
        eps = ctx.fundamental("eps")
        pe = (ctx.price / eps.where(eps > 0)).where(ctx.members)  # in-universe, tradable, EPS>0

        cheap = pe.rank(axis=1, method="first")                   # 1 = lowest P/E (cheapest → long)
        rich = pe.rank(axis=1, ascending=False, method="first")   # 1 = highest P/E (richest → short)
        longs = cheap.le(self.n) & pe.notna()
        shorts = rich.le(self.n) & pe.notna()

        weights = longs.astype(float) / self.n - shorts.astype(float) / self.n
        enough = pe.notna().sum(axis=1) >= 2 * self.n             # need a full long & short leg
        weights = weights.mul(enough.astype(float), axis=0)

        # Decide on day t, act on t+1 — the lag that prevents look-ahead.
        return weights.shift(1).fillna(0.0)
