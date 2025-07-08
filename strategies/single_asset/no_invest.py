from abc import ABC
from typing import Dict

import pandas as pd

from contracts.asset import Asset, CashAsset
from core.market_data import MarketData
from strategies.base import StrategyBase, StrategyFactory


@StrategyFactory.register("hold_cash")
class HoldCashStrategy(StrategyBase, ABC):
    def __init__(self, **kwargs):
        self.lookback_period = 0

    def get_name(self) -> str:
        return "hold_cash"

    def get_config(self) -> Dict:
        return {
            "type": "hold_cash",
            "name": self.get_name()
        }

    def generate_signals(self, price_data: pd.DataFrame | Dict[str, pd.DataFrame],
                         current_date: pd.Timestamp, positions: Dict[str, Asset],
                         cash: float, **kwargs) -> None:
        """
        Buy once and hold till perpetuity for the strategy.
        :param price_data: A DataFrame or dict of DataFrames containing price data for each asset.
        :param cash:
        :param **kwargs:
        :param current_date:
        :param positions:
        :return:
        """
        return
