from abc import ABC
from typing import Dict

import pandas as pd

from contracts.asset import Asset, CashAsset
from core.market_data import MarketData
from strategies.stock.base import StrategyBase, StrategyFactory


@StrategyFactory.register("buy_n_hold")
class BuyNHoldStrategy(StrategyBase, ABC):
    def __init__(self, **kwargs):
        self.lookback_period = 1
        self.has_bought = set()

    def get_name(self) -> str:
        return "buy_n_hold"

    def get_config(self) -> Dict:
        return {
            "type": "buy_n_hold",
            "name": self.get_name()
        }

    def generate_signals(self, price_data: pd.DataFrame | Dict[str, pd.DataFrame], current_date: pd.Timestamp,
                         positions: Dict[str, Asset], cash: float, **kwargs) -> Dict[str, int]:
        """
        Buy once and hold till perpetuity for the strategy.
        :param price_data: A DataFrame or dict of DataFrames containing price data for each asset.
        :param cash:
        :param **kwargs:
        :param current_date:
        :param positions:
        :return:
        """
        if len(self.has_bought) > 0:
            # If already bought, no further action
            return {}

        ticker = list(positions.keys())[0]  # Single ticker strategy

        # Allocate all cash to the first asset
        order_qty = cash // price_data[ticker]['Close'].loc[current_date]
        if order_qty > 0:
            return {ticker: int(order_qty)}
        self.has_bought.add(ticker)
