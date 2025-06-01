from typing import List
import pandas as pd

from core.executor import PortfolioExecutor
from core.guardrails.base import Guardrail
from core.market_data import MarketData
from contracts.portfolio import Portfolio


class Backtester:
    def __init__(self, strategy, market_data: MarketData, starting_cash=100000.0, guardrails: List[Guardrail] = None):
        self.strategy = strategy
        self.market_data = market_data

        # Initialize portfolio and executor separately
        self.portfolio = Portfolio(
            name="BacktestPortfolio",
            tickers=market_data.get_available_symbols(),
            starting_cash=starting_cash,
            strategy=strategy,
            metadata={"source": "Backtester"}
        )
        self.executor = PortfolioExecutor(portfolio=self.portfolio, market_data=market_data, guardrails=guardrails)

        self.tickers = []
        self.start_date = None
        self.end_date = None
        self.signals = {}

    def run(self, tickers: List[str], start_date: str, end_date: str):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date

        # Determine common index (trading calendar)
        price_frames = [self.market_data.get_series(tic) for tic in tickers]
        common_index = price_frames[0].index
        for df in price_frames[1:]:
            common_index = common_index.intersection(df.index)
        common_index = common_index.sort_values()

        for current_date in common_index:
            self.executor.execute_trades(current_date)
            self.executor.update_equity(current_date)

    def get_trade_log(self) -> pd.DataFrame:
        return self.portfolio.get_trade_log()

    def get_equity_curve(self) -> pd.DataFrame:
        return self.executor.get_equity_curve()

    def get_final_net_worth(self) -> float:
        return self.get_equity_curve()['net_worth'].iloc[-1]

    def get_market_data(self) -> MarketData:
        return self.market_data
