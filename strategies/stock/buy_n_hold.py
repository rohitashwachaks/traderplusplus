from abc import ABC
from typing import Dict

import pandas as pd

from contracts.asset import Asset, CashAsset
from core.market_data import MarketData
from strategies.stock.base import StrategyBase, StrategyFactory


@StrategyFactory.register("buy_n_hold")
class BuyNHoldStrategy(StrategyBase, ABC):
    def __init__(self, **kwargs):
        self.has_bought = set()

    def get_name(self) -> str:
        return "buy_n_hold"

    def get_config(self) -> Dict:
        return {
            "type": "buy_n_hold",
            "name": self.get_name()
        }

    def generate_signals(self, market_data: MarketData, current_date: pd.Timestamp,
                         positions: Dict[str, Asset | CashAsset]) -> Dict[str, int]:
        """
        Evenly distribute cash across all assets in the portfolio.
        :param **kwargs:
        :param market_data:
        :param current_date:
        :param positions:
        :return:
        """
        networth = sum(
            asset.balance * market_data.get_price(asset.ticker, current_date)
            for ticker, asset in positions.items()
        )

        allocation_per_asset = networth / len([ticker for ticker in positions if isinstance(positions[ticker], Asset)])

        desired_allocation = {
            ticker: allocation_per_asset // market_data.get_price(ticker, current_date)
            for ticker in positions if isinstance(positions[ticker], Asset)
        }

        signals = {
            ticker: int(desired_allocation[ticker] - positions[ticker].shares)
            for ticker in desired_allocation
        }

        return signals
