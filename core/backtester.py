from typing import List, Optional
import pandas as pd
from tqdm import tqdm

from executors.backtest import BacktestExecutor
from executors.base import BaseExecutor
from core.market_data import MarketData
from contracts.portfolio import Portfolio
from contracts.order import Order, OrderSide, OrderType
from strategies.base import StrategyBase


class Backtester:
    """
    Backtester runs a backtest using a given strategy, market data, and portfolio.
    It generates trading signals based on the strategy and submits orders to the executor.
    The executor handles order execution and portfolio updates.
    It does not handle analytics or performance evaluation directly.
    The backtester is designed to be flexible and can work with any strategy that implements the StrategyBase interface.
    It can also be used with different executors, such as BacktestExecutor or PaperExecutor.
    The backtester runs through the specified date range, generating signals for each ticker and executing trades accordingly.
    """
    def __init__(self, strategy: 'StrategyBase',
                 market_data: MarketData,
                 portfolio: Portfolio,
                 executor: 'BaseExecutor',
                 **executor_kwargs):
        """
        :param strategy:
        :param market_data:
        :param portfolio:
        :param executor:
        :param executor_kwargs:
        """
        self.strategy = strategy
        self.market_data = market_data
        self.portfolio = portfolio
        self.executor = executor

        self.tickers = portfolio.tickers
        self.signals = {}

    def run(self, end_date: str, start_date: Optional[str] = None, interval='1d', period='5y'):

        # Fetch market data for all tickers
        # check for strategy lok-back period, if any, and adjust start_date accordingly
        if hasattr(self.strategy, 'lookback_period'):
            lookback_period = self.strategy.lookback_period
            if isinstance(lookback_period, int):
                # Convert lookback period to a date offset
                start_date = (pd.to_datetime(start_date) - pd.DateOffset(days=(self.strategy.lookback_period+1))).strftime('%Y-%m-%d')
            else:
                raise ValueError("lookback_period must be an integer representing days")
        self.market_data.get_market_data(self.tickers + [self.portfolio.benchmark],
                                         start_date=start_date, end_date=end_date,
                                         interval=interval, period=period)

        # Iterate through the common index dates
        for current_date in tqdm(self.market_data.dates):
            try:
                # Generate slice of
                # --- MARKET DATA: FETCH HISTORICAL DATA FOR ALL TICKERS ---
                # current_date = pd.to_datetime(current_date)

                historical_data = self.market_data.get_history(self.tickers, lookback=self.strategy.lookback_period, end_date=current_date)
                if not historical_data:
                    continue

                # current_date = historical_data.iloc[-1].name

                # --- PURE STRATEGY: ONLY GENERATE SIGNALS ---
                signals = self.strategy.generate_signals(historical_data, current_date=current_date,
                                                         positions=self.portfolio.positions, cash=self.portfolio.cash)
                # --- EXECUTOR: SUBMIT ORDERS BASED ON SIGNALS ---
                if signals:
                    for symbol, order_size in signals.items():
                        if order_size == 0:
                            continue
                        order_side = OrderSide.BUY if order_size > 0 else OrderSide.SELL
                        if order_side is not None:
                            order = Order(
                                ticker=symbol,
                                side=order_side,
                                quantity=abs(order_size),  # Use absolute value for quantity
                                order_type=OrderType.MARKET
                            )
                            self.executor.submit_order(order)

                # --- EXECUTOR: ADVANCE TO NEXT STEP ---
                self.executor.step(current_date)
            except Exception as e:
                print(f"Error during backtest step for {current_date}: {e}")
                continue

        # --- EXECUTOR: FINALIZE ---
        print("Finalizing backtest...")

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
