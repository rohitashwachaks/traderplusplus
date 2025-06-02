from typing import List
import pandas as pd
from core.market_data import MarketData
from contracts.portfolio import Portfolio
from contracts.order import Order, OrderSide, OrderType


class Backtester:
    def __init__(self, strategy, market_data: MarketData, starting_cash=100000.0, executor=None, **executor_kwargs):
        self.strategy = strategy
        self.market_data = market_data
        self.portfolio = Portfolio(
            name="BacktestPortfolio",
            tickers=market_data.get_available_symbols(),
            starting_cash=starting_cash,
            strategy=strategy,
            metadata={"source": "Backtester"}
        )
        if executor is not None:
            self.executor = executor
        else:
            from core.executors.backtest import BacktestExecutor
            self.executor = BacktestExecutor(portfolio=self.portfolio, market_data=market_data, **executor_kwargs)
        self.tickers = []
        self.start_date = None
        self.end_date = None
        self.signals = {}

    def run(self, tickers: List[str], start_date: str, end_date: str):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        price_frames = [self.market_data.get_series(tic) for tic in tickers]
        common_index = price_frames[0].index
        for df in price_frames[1:]:
            common_index = common_index.intersection(df.index)
        common_index = common_index.sort_values()
        for current_date in common_index:
            # --- PURE STRATEGY: ONLY GENERATE SIGNALS ---
            signals = self.strategy.generate_signals(self.market_data, current_date=current_date)
            # --- EXECUTOR: SUBMIT ORDERS BASED ON SIGNALS ---
            for symbol, signal in signals.items():
                if signal == 1:
                    order = Order(symbol=symbol, side=OrderSide.BUY, quantity=1, order_type=OrderType.MARKET)
                    self.executor.submit_order(order)
                elif signal == -1:
                    order = Order(symbol=symbol, side=OrderSide.SELL, quantity=1, order_type=OrderType.MARKET)
                    self.executor.submit_order(order)
            # --- EXECUTOR: ADVANCE TO NEXT STEP ---
            self.executor.step(current_date)

    def get_trade_log(self) -> pd.DataFrame:
        return self.portfolio.get_trade_log()

    def get_equity_curve(self) -> pd.DataFrame:
        return self.executor.get_equity_curve()

    def get_final_net_worth(self) -> float | None:
        eq_curve = self.get_equity_curve()
        if eq_curve is not None:
            return eq_curve['net_worth'].iloc[-1]
        return None

    def get_market_data(self) -> MarketData:
        return self.market_data

# ---
# USAGE EXAMPLE (for doc/reference):
#
# backtester = Backtester(strategy, market_data, starting_cash=100000, executor=BacktestExecutor(...))
# backtester.run(["AAPL", "MSFT"], start_date="2022-01-01", end_date="2022-12-31")
# trade_log = backtester.get_trade_log()
# equity_curve = backtester.get_equity_curve()
# ---
