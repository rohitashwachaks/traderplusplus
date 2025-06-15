from .base import BaseExecutor
from contracts.order import Order, OrderResult, OrderStatus, OrderType
from contracts.portfolio import Portfolio
from contracts.asset import Asset, CashAsset
from datetime import datetime
import uuid

from ..market_data import MarketData


class PaperExecutor(BaseExecutor):
    def __init__(self, portfolio: Portfolio, slippage: float = 0.0, market_data: MarketData =None):
        self._slippage = slippage
        self.portfolio = portfolio
        self.market_data = market_data
        self.orders = {}  # order_id -> Order
        self.order_status = {}  # order_id -> OrderStatus
        self.fills = {}  # order_id -> OrderResult

    def submit_order(self, order: Order):
        order_id = order.client_order_id or str(uuid.uuid4())
        order.client_order_id = order_id
        self.orders[order_id] = order
        self.order_status[order_id] = OrderStatus.SUBMITTED
        # Orders are not filled instantly; fill in step()
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
        # No-op for paper trading
        pass

    def step(self, current_time):
        # Attempt to fill open orders
        for order_id, order in list(self.orders.items()):
            if self.order_status[order_id] != OrderStatus.SUBMITTED:
                continue
            price = self.market_data.get_price(order.ticker, current_time)
            if price is None:
                continue
            fill_qty = order.quantity  # For now, assume full fill (can add partial fill logic)
            avg_fill_price = price

            # Simulate slippage
            if order.side.name == 'BUY':
                avg_fill_price *= (1 + self._slippage)
            elif order.side.name == 'SELL':
                avg_fill_price *= (1 - self._slippage)

            # Update portfolio
            try:
                if order.side.name == 'BUY':
                    self.portfolio.execute_trade(current_time, order.ticker, 'BUY', fill_qty, avg_fill_price,
                                                 note='Paper Fill')
                else:
                    self.portfolio.execute_trade(current_time, order.ticker, 'SELL', fill_qty, avg_fill_price,
                                                 note='Paper Fill')
                self.order_status[order_id] = OrderStatus.FILLED
                self.fills[order_id] = OrderResult(order_id=order_id, status=OrderStatus.FILLED,
                                                   filled_quantity=fill_qty, avg_fill_price=avg_fill_price)
            except Exception as e:
                self.order_status[order_id] = OrderStatus.REJECTED
                self.fills[order_id] = OrderResult(order_id=order_id, status=OrderStatus.REJECTED, message=str(e))
