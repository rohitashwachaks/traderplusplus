"""Strategy-attached guardrails: a strategy ships its own risk overlays, no CLI needed."""
import pandas as pd

from core.context import DataContext
from engine.runner import target_weights
from guardrails.base import Guardrail
from strategies.buy_n_hold import BuyAndHold


class Halver(Guardrail):
    name = "halver"

    def apply(self, prices: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
        return weights * 0.5


def test_attached_guardrails_apply_without_cli(rising_prices):
    strategy = BuyAndHold()
    strategy.guardrails = (Halver(),)
    ctx = DataContext.from_prices(rising_prices)

    plain = target_weights(BuyAndHold(), ctx)
    guarded = target_weights(strategy, ctx)

    pd.testing.assert_frame_equal(guarded, plain * 0.5)


def test_attached_and_external_guardrails_compose(rising_prices):
    strategy = BuyAndHold()
    strategy.guardrails = (Halver(),)
    ctx = DataContext.from_prices(rising_prices)

    guarded = target_weights(strategy, ctx, guardrails=[Halver()])  # attached, then external
    plain = target_weights(BuyAndHold(), ctx)

    pd.testing.assert_frame_equal(guarded, plain * 0.25)
