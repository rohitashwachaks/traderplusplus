from abc import ABC
from typing import Dict

import pandas as pd

from core.market_data import MarketData
from strategies.stock.base import StrategyBase, StrategyFactory


@StrategyFactory.register("buy_n_hold")
class BuyNHoldStrategy(StrategyBase, ABC):
    def __init__(self):
        self.has_bought = set()

    def get_name(self) -> str:
        return "buy_n_hold"

    def get_config(self) -> Dict:
        return {
            "type": "buy_n_hold",
            "name": self.get_name()
        }

    def generate_signals(
            self,
            market_data: MarketData,
            current_date: pd.Timestamp,
            lookback_window: int = 60
    ) -> Dict[str, int]:
        signals = {}
        for ticker in market_data.get_available_symbols():
            if ticker not in self.has_bought:
                signals[ticker] = 1
                self.has_bought.add(ticker)
            else:
                signals[ticker] = 0
        return signals
