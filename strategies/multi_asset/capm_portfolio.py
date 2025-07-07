from typing import Dict, Optional

import pandas as pd

from contracts.asset import Asset
from strategies.stock.base import StrategyBase, StrategyFactory


@StrategyFactory.register("capm")
class CAPMStrategy(StrategyBase):
    def __init__(self, algo):
        self.algo = algo

    def get_name(self) -> str:
        return "CAPM Portfolio Strategy"

    def generate_signals(self, price_data: pd.DataFrame | Dict[str, pd.DataFrame],
                         current_date: pd.Timestamp, positions: Dict[str, Asset],
                         cash: float, **kwargs) -> Optional[Dict[str, int]]:
        signals = {}
        for ticker, df in price_data.items():
            df = df.copy()
            df['signal'] = 0  # Placeholder for CAPM signals
            df['position'] = 0  # Placeholder for positions
            signals[ticker] = df
        return signals
