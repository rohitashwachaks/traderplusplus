import pandas as pd

from core.context import DataContext
from strategies.base import TargetWeightStrategy, register


@register("buy_n_hold")
class BuyAndHold(TargetWeightStrategy):
    """Hold every in-universe name at equal weight. With a static all-in universe this is the
    classic buy-once-and-hold; with a real membership mask it equal-weights the current members.

    **Reference:** Benchmark strategy. No academic paper — used to measure excess returns.
    """

    name = "buy_n_hold"

    def weights(self, ctx: DataContext) -> pd.DataFrame:
        held = ctx.members.astype(float)
        count = held.sum(axis=1)
        return held.div(count.where(count > 0), axis=0).fillna(0.0)
