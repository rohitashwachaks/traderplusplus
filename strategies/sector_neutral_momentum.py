import pandas as pd

from core.context import DataContext
from strategies import grouping
from strategies.base import TargetWeightStrategy, register


@register("sector_neutral_momentum")
class SectorNeutralMomentum(TargetWeightStrategy):
    """Cross-industry momentum: hold the top-``top_n`` trailing-return names in **each** group.

    Plain cross-sectional momentum lets one hot industry crowd the whole book — in a tech
    melt-up you own ten software names and nothing else. This ranks momentum *within* each
    group (``sector`` from GICS by default, or ``sic2`` / ``industry``) and holds the leaders
    of every group equal-weighted, so the portfolio always spans industries and the bet is
    "winners relative to their peers," not "whichever sector ran hardest."

    The grouping is **static** (today's labels applied to all history) — a labeled
    classification bias, surfaced on every report that uses it.

    **Reference:** Moskowitz & Grinblatt (1999). "Do Industries Explain Momentum?" Journal of
    Finance. https://www.jstor.org/stable/2697722 — momentum has a strong industry component;
    ranking within groups isolates the name-vs-peer signal.
    """

    name = "sector_neutral_momentum"
    rebalance_freq = "M"
    reconstitution_freq = "M"

    def __init__(self, lookback: int = 60, top_n: int = 1, group_by: str = "sector"):
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        if top_n < 1:
            raise ValueError("top_n must be >= 1")
        self.lookback = lookback
        self.top_n = top_n
        self.group_by = group_by
        self.requires_meta = (group_by,)

    def weights(self, ctx: DataContext) -> pd.DataFrame:
        prices = ctx.price.where(ctx.members)          # rank only in-universe, tradable names
        groups = grouping.group_series(ctx, self.group_by)
        momentum = prices.pct_change(self.lookback)

        selected = grouping.top_per_group(momentum, groups, self.top_n, ascending=False)
        count = selected.sum(axis=1)
        weights = selected.div(count.where(count > 0), axis=0).fillna(0.0)

        # Decide on day t's close, act on t+1 — the lag that prevents look-ahead.
        return weights.shift(1).fillna(0.0)
