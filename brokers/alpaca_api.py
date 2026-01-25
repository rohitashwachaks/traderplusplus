import os
import requests
from dotenv import load_dotenv
from contracts.order import Order, OrderStatus
import logging
import time


class AlpacaBrokerAPI:
    """
    Broker API interface for Alpaca. Loads API credentials from environment or .env file.
    Implements methods required by LiveExecutor: submit_order, cancel_order, get_order_status, get_positions, get_fill_info.
    Now includes error handling, basic logging, and a streaming price method (websocket).
    """

    def __init__(self, config_path=None, log_level=logging.INFO, paper_trading=True):
        # Load credentials from .env or config
        if config_path is not None and config_path.endswith('.env'):
            load_dotenv(config_path)
        else:
            load_dotenv()
        
        # Set base URL based on paper_trading flag
        if paper_trading:
            self.base_url = os.getenv('ALPACA_PAPER_BASE_URL', 'https://paper-api.alpaca.markets')
            self.data_url = os.getenv('ALPACA_DATA_URL', 'https://data.alpaca.markets')
        else:
            self.base_url = os.getenv('ALPACA_LIVE_BASE_URL', 'https://api.alpaca.markets')
            self.data_url = os.getenv('ALPACA_DATA_URL', 'https://data.alpaca.markets')
        
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_API_SECRET')
        self.paper_trading = paper_trading
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing Alpaca API credentials. Please set ALPACA_API_KEY and ALPACA_API_SECRET.")
        
        self.session = requests.Session()
        self.session.headers.update({
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret
        })
        
        self.logger = logging.getLogger("AlpacaBrokerAPI")
        self.logger.setLevel(log_level)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s'))
        if not self.logger.hasHandlers():
            self.logger.addHandler(handler)
        
        self.logger.info(f"Initialized Alpaca API in {'PAPER' if paper_trading else 'LIVE'} mode")
        self.logger.info(f"Base URL: {self.base_url}")

    def submit_order(self, order: Order):
        side = order.side.name.lower()
        type_ = order.order_type.name.lower()
        data = {
            "ticker": order.ticker,
            "qty": order.quantity,
            "side": side,
            "type": type_,
            "time_in_force": order.time_in_force or "gtc"
        }
        if order.limit_price:
            data["limit_price"] = order.limit_price
        if order.stop_price:
            data["stop_price"] = order.stop_price
        try:
            resp = self.session.post(f"{self.base_url}/v2/orders", json=data)
            resp.raise_for_status()
            self.logger.info(f"Order submitted: {data}")
            return resp.json()
        except Exception as e:
            self.logger.error(f"Order submission failed: {data}, error: {e}")
            raise

    def cancel_order(self, order_id):
        try:
            resp = self.session.delete(f"{self.base_url}/v2/orders/{order_id}")
            resp.raise_for_status()
            self.logger.info(f"Order cancelled: {order_id}")
            return resp.json()
        except Exception as e:
            self.logger.error(f"Cancel order failed: {order_id}, error: {e}")
            raise

    def get_order_status(self, order_id):
        try:
            resp = self.session.get(f"{self.base_url}/v2/orders/{order_id}")
            resp.raise_for_status()
            status = resp.json()["status"]
            mapping = {
                "new": OrderStatus.SUBMITTED,
                "partially_filled": OrderStatus.PARTIALLY_FILLED,
                "filled": OrderStatus.FILLED,
                "canceled": OrderStatus.CANCELLED,
                "rejected": OrderStatus.REJECTED,
                "pending_cancel": OrderStatus.CANCELLED,
                "pending_replace": OrderStatus.SUBMITTED,
            }
            self.logger.info(f"Order status for {order_id}: {status}")
            return mapping.get(status, OrderStatus.NEW)
        except Exception as e:
            self.logger.error(f"Get order status failed: {order_id}, error: {e}")
            raise

    def get_positions(self):
        try:
            resp = self.session.get(f"{self.base_url}/v2/positions")
            resp.raise_for_status()
            self.logger.info("Fetched positions.")
            return resp.json()
        except Exception as e:
            self.logger.error(f"Get positions failed: {e}")
            raise

    def get_fill_info(self, order_id):
        try:
            resp = self.session.get(f"{self.base_url}/v2/orders/{order_id}")
            resp.raise_for_status()
            order = resp.json()
            self.logger.info(f"Fetched fill info for {order_id}")
            return {
                "filled_quantity": float(order.get("filled_qty", 0)),
                "avg_fill_price": float(order.get("filled_avg_price", 0)),
            }
        except Exception as e:
            self.logger.error(f"Get fill info failed: {order_id}, error: {e}")
            raise

    def get_account(self):
        """
        Fetches account information including buying power, cash, and equity.
        """
        try:
            resp = self.session.get(f"{self.base_url}/v2/account")
            resp.raise_for_status()
            account = resp.json()
            self.logger.info("Fetched account information")
            return account
        except Exception as e:
            self.logger.error(f"Get account failed: {e}")
            raise

    def test_connection(self):
        """
        Tests the connection to Alpaca API by fetching account info.
        Returns True if successful, raises exception otherwise.
        """
        try:
            account = self.get_account()
            self.logger.info("Connection test successful")
            return True, account
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False, str(e)

    def get_clock(self):
        """
        Gets the market clock to check if market is open.
        """
        try:
            resp = self.session.get(f"{self.base_url}/v2/clock")
            resp.raise_for_status()
            clock = resp.json()
            self.logger.info(f"Market is {'OPEN' if clock['is_open'] else 'CLOSED'}")
            return clock
        except Exception as e:
            self.logger.error(f"Get clock failed: {e}")
            raise

    def get_asset(self, symbol):
        """
        Gets information about a specific asset/symbol.
        """
        try:
            resp = self.session.get(f"{self.base_url}/v2/assets/{symbol}")
            resp.raise_for_status()
            asset = resp.json()
            self.logger.info(f"Fetched asset info for {symbol}")
            return asset
        except Exception as e:
            self.logger.error(f"Get asset failed for {symbol}: {e}")
            raise

    def get_latest_trade(self, symbol):
        """
        Gets the latest trade for a symbol.
        """
        try:
            resp = self.session.get(f"{self.data_url}/v2/stocks/{symbol}/trades/latest")
            resp.raise_for_status()
            trade = resp.json()
            self.logger.info(f"Fetched latest trade for {symbol}")
            return trade
        except Exception as e:
            self.logger.error(f"Get latest trade failed for {symbol}: {e}")
            raise

    def validate_credentials(self):
        """
        Validates API credentials and returns account status.
        """
        try:
            account = self.get_account()
            return {
                'valid': True,
                'account_number': account.get('account_number'),
                'status': account.get('status'),
                'trading_blocked': account.get('trading_blocked'),
                'account_blocked': account.get('account_blocked'),
                'pattern_day_trader': account.get('pattern_day_trader'),
                'cash': float(account.get('cash', 0)),
                'buying_power': float(account.get('buying_power', 0)),
                'equity': float(account.get('equity', 0)),
                'paper_trading': self.paper_trading
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    def stream_quotes(self, symbols, on_quote, on_error=None):
        """
        Streams real-time quotes for the given symbols using Alpaca's websocket API.
        Calls on_quote(quote_dict) for each quote update. (Requires websocket-client)
        """
        import websocket
        import json
        ws_url = "wss://stream.data.alpaca.markets/v2/sip"
        headers = [
            f"Authorization: Bearer {self.api_key}:{self.api_secret}"
        ]

        def on_open(ws):
            auth_msg = {
                "action": "auth",
                "key": self.api_key,
                "secret": self.api_secret
            }
            ws.send(json.dumps(auth_msg))
            sub_msg = {"action": "subscribe", "quotes": symbols}
            ws.send(json.dumps(sub_msg))
            self.logger.info(f"Subscribed to quotes: {symbols}")

        def on_message(ws, message):
            data = json.loads(message)
            if isinstance(data, list):
                for item in data:
                    if item.get('T') == 'q':
                        on_quote(item)
            elif isinstance(data, dict) and data.get('T') == 'q':
                on_quote(data)

        def on_error_ws(ws, error):
            self.logger.error(f"Websocket error: {error}")
            if on_error:
                on_error(error)

        ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=on_error_ws)
        ws.run_forever()
