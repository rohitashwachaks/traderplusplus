from .base import BaseExecutor
from contracts.order import Order, OrderResult, OrderStatus
from contracts.portfolio import Portfolio
from core.market_data import MarketData
import uuid


class LiveExecutor(BaseExecutor):
    def __init__(self, portfolio: Portfolio, broker_api, market_data: MarketData = None):
        self.portfolio = portfolio
        self.market_data = market_data
        self.broker_api = broker_api  # Should implement submit_order, cancel_order, get_order_status, sync_portfolio
        self.orders = {}  # order_id -> Order
        self.order_status = {}  # order_id -> OrderStatus
        self.fills = {}  # order_id -> OrderResult

    def submit_order(self, order: Order):
        order_id = order.client_order_id or str(uuid.uuid4())
        order.client_order_id = order_id
        broker_resp = self.broker_api.submit_order(order)
        self.orders[order_id] = order
        self.order_status[order_id] = OrderStatus.SUBMITTED
        return order_id

    def cancel_order(self, order_id):
        if order_id in self.orders and self.order_status[order_id] not in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            self.broker_api.cancel_order(order_id)
            self.order_status[order_id] = OrderStatus.CANCELLED
            return True
        return False

    def get_portfolio(self):
        # Sync portfolio with broker
        self.sync_portfolio()
        return self.portfolio

    def get_order_status(self, order_id):
        # Query broker for latest status
        status = self.broker_api.get_order_status(order_id)
        self.order_status[order_id] = status
        return status

    def sync_portfolio(self):
        # Update local portfolio with broker positions (user must implement this in broker_api)
        broker_positions = self.broker_api.get_positions()
        self.portfolio.sync_with_broker(broker_positions)

    def step(self, current_time):
        # In live trading, step could poll for fills and update portfolio
        for order_id, order in list(self.orders.items()):
            status = self.get_order_status(order_id)
            if status == OrderStatus.FILLED and order_id not in self.fills:
                fill_info = self.broker_api.get_fill_info(order_id)
                self.fills[order_id] = OrderResult(order_id=order_id, status=OrderStatus.FILLED,
                                                   filled_quantity=fill_info['filled_quantity'],
                                                   avg_fill_price=fill_info['avg_fill_price'])
                # Update portfolio if desired (optional; broker_portfolio is source of truth)
