from typing import Dict

import pandas as pd

from strategies.stock.base import StrategyBase, StrategyFactory


@StrategyFactory.register("capm")
class CAPMStrategy(StrategyBase):
    def __init__(self, algo):
        self.algo = algo

    def get_name(self) -> str:
        return "CAPM Portfolio Strategy"

    def generate_signals(self, market_data: Dict[str, pd.DataFrame], cash) -> Dict[str, pd.DataFrame]:
        signals = {}
        for ticker, df in market_data.items():
            df = df.copy()
            df['signal'] = 0  # Placeholder for CAPM signals
            df['position'] = 0  # Placeholder for positions
            signals[ticker] = df
        return signals

    def generate_allocations(
            self,
            signals: Dict[str, pd.DataFrame],
            portfolio_cash: float,
            market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, int]:
        allocations = self.algo.maximise_sharpe()
        return allocations
