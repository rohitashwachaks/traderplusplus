from .base import BaseExecutor
from contracts.order import Order, OrderResult, OrderStatus, OrderType
from contracts.portfolio import Portfolio
from core.guardrails.base import Guardrail
from core.market_data import MarketData
from datetime import datetime
import pandas as pd
import uuid


class BacktestExecutor(BaseExecutor):
    """
    BacktestExecutor simulates order execution in a backtesting environment.
    It processes orders based on historical market data and portfolio state.
    It supports order submission, cancellation, and tracking of order status and fills.
    It does not interact with any live market or broker API.
    Instead, it simulates order execution by filling orders at historical prices.
    """
    def __init__(self, portfolio: Portfolio, market_data: MarketData, guardrails=None):
        self.portfolio = portfolio
        self.market_data = market_data
        self.guardrails = guardrails or []
        self.orders = {}  # order_id -> Order
        self.order_status = {}  # order_id -> OrderStatus
        self.fills = {}  # order_id -> OrderResult
        self.equity_curve = []

    def submit_order(self, order: Order):
        order_id = order.client_order_id or str(uuid.uuid4())
        order.client_order_id = order_id
        self.orders[order_id] = order
        self.order_status[order_id] = OrderStatus.SUBMITTED
        return order_id

    def cancel_order(self, order_id):
        if order_id in self.orders and self.order_status[order_id] not in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            self.order_status[order_id] = OrderStatus.CANCELLED
            return True
        return False

    def get_portfolio(self):
        return self.portfolio

    def get_order_status(self, order_id):
        return self.order_status.get(order_id, OrderStatus.NEW)

    def sync_portfolio(self):
        pass

    def step(self, current_time):
        # Fill all submitted orders instantly at historical price (simulate perfect fill)
        for order_id, order in list(self.orders.items()):
            if self.order_status[order_id] != OrderStatus.SUBMITTED:
                continue

            price = self.market_data.get_price(order.ticker, current_time)[order.ticker]

            if price is None:
                continue
            fill_qty = order.quantity
            avg_fill_price = price
            # Guardrails (if any)
            for guardrail in self.guardrails:
                if hasattr(guardrail, 'evaluate') and not guardrail.evaluate(self.portfolio.positions,
                                                                             {order.ticker: price}):
                    self.order_status[order_id] = OrderStatus.REJECTED
                    self.fills[order_id] = OrderResult(order_id=order_id, status=OrderStatus.REJECTED,
                                                       message='Guardrail blocked order')
                    continue
            try:
                self.portfolio.execute_trade(current_time, order, avg_fill_price, note='Backtest Fill')

                self.order_status[order_id] = OrderStatus.FILLED
                self.fills[order_id] = OrderResult(order_id=order_id, status=OrderStatus.FILLED,
                                                   filled_quantity=fill_qty, avg_fill_price=avg_fill_price)

            except Exception as e:
                self.order_status[order_id] = OrderStatus.REJECTED
                self.fills[order_id] = OrderResult(order_id=order_id, status=OrderStatus.REJECTED, message=str(e))

        # Track equity
        price = self.market_data.get_price(self.portfolio.tickers, current_time)
        net_worth = self.portfolio.net_worth(price)
        benchmark_price = self.market_data.get_price(self.portfolio.benchmark, current_time)[self.portfolio.benchmark]

        self.equity_curve.append({'date': current_time, 'net_worth': net_worth, 'benchmark': benchmark_price})

    def get_equity_curve(self):
        df = pd.DataFrame(self.equity_curve, columns=['date', 'net_worth', 'benchmark'])
        df.set_index('date', inplace=True)
        return df
