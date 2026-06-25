import pandas as pd

from core.context import DataContext
from strategies.base import TargetWeightStrategy, register


@register("xs_momentum")
class CrossSectionalMomentum(TargetWeightStrategy):
    """Rank a basket by trailing return and hold the top names, equal-weighted.

    A cross-sectional ("relative strength") momentum portfolio: each period, buy the recent
    winners and drop the laggards. Meant for a basket of tickers — with one or two names it
    degenerates. Defaults to a monthly rebalance/reconstitution (override via the strategy's
    freq attributes or the CLI). Downside is left to a stop-loss guardrail, not a sign filter.
    """

    name = "xs_momentum"
    rebalance_freq = "M"
    reconstitution_freq = "M"

    def __init__(self, lookback: int = 120, top_n: int | None = None):
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        if top_n is not None and top_n < 1:
            raise ValueError("top_n must be >= 1 or None")
        self.lookback = lookback
        self.top_n = top_n

    def weights(self, ctx: DataContext) -> pd.DataFrame:
        prices = ctx.price.where(ctx.members)  # rank only among in-universe names
        momentum = prices.pct_change(self.lookback)
        n = self.top_n or max(1, prices.shape[1] // 2)

        ranks = momentum.rank(axis=1, ascending=False, method="first")
        selected = ranks.le(n) & momentum.notna()
        count = selected.sum(axis=1)
        weights = selected.div(count.where(count > 0), axis=0).fillna(0.0)

        # Decide on day t's close, act on t+1 — this lag is what prevents look-ahead.
        return weights.shift(1).fillna(0.0)
