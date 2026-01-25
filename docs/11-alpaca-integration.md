# Alpaca Integration Guide

This guide covers the integration with Alpaca for both paper and live trading.

## Overview

The Alpaca integration provides:
- Paper trading for risk-free testing
- Live trading for real market execution
- Real-time market data
- Position and account management
- Order execution and tracking

## Setup

### 1. Get API Keys

**Paper Trading (Recommended for Testing):**
1. Sign up at [Alpaca](https://alpaca.markets/)
2. Navigate to [Paper Trading Dashboard](https://app.alpaca.markets/paper/dashboard/overview)
3. Generate API keys from the dashboard

**Live Trading (Use with Caution):**
1. Complete account verification
2. Navigate to [Live Trading Dashboard](https://app.alpaca.markets/live/dashboard/overview)
3. Generate API keys from the dashboard

### 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your API credentials:
```bash
ALPACA_API_KEY=your_api_key_here
ALPACA_API_SECRET=your_api_secret_here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Paper Trading

```python
from brokers.alpaca_api import AlpacaBrokerAPI

# Initialize for paper trading (default)
broker = AlpacaBrokerAPI(paper_trading=True)

# Test connection
success, account = broker.test_connection()
if success:
    print(f"Connected! Account: {account['account_number']}")

# Get account info
account = broker.get_account()
print(f"Buying Power: ${account['buying_power']}")
print(f"Cash: ${account['cash']}")

# Check market status
clock = broker.get_clock()
print(f"Market is {'OPEN' if clock['is_open'] else 'CLOSED'}")

# Get positions
positions = broker.get_positions()
for pos in positions:
    print(f"{pos['symbol']}: {pos['qty']} shares")
```

### Live Trading

```python
from brokers.alpaca_api import AlpacaBrokerAPI

# Initialize for live trading
broker = AlpacaBrokerAPI(paper_trading=False)

# Validate credentials
validation = broker.validate_credentials()
if validation['valid']:
    print("Live trading credentials validated")
    print(f"Account Status: {validation['status']}")
    print(f"Trading Blocked: {validation['trading_blocked']}")
else:
    print(f"Validation failed: {validation['error']}")
```

### Placing Orders

```python
from contracts.order import Order, OrderSide, OrderType

# Create a market order
order = Order(
    ticker="AAPL",
    quantity=10,
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    time_in_force="gtc"
)

# Submit order
order_id = broker.submit_order(order)
print(f"Order submitted: {order_id}")

# Check order status
status = broker.get_order_status(order_id)
print(f"Order status: {status}")

# Cancel order (if needed)
broker.cancel_order(order_id)
```

### Getting Market Data

```python
# Get asset information
asset = broker.get_asset("AAPL")
print(f"Symbol: {asset['symbol']}")
print(f"Tradable: {asset['tradable']}")
print(f"Marginable: {asset['marginable']}")

# Get latest trade
trade = broker.get_latest_trade("AAPL")
print(f"Latest price: ${trade['trade']['p']}")
```

## Testing the Integration

Run the test suite using pytest:

```bash
# Run all tests
pytest tests/ -v

# Run only connection tests
pytest tests/test_alpaca_connection.py -v

# Run specific test
pytest tests/test_alpaca_connection.py::TestAlpacaConnection::test_connection -v
```

This will test:
- ✓ Connection to Alpaca API
- ✓ Account information retrieval
- ✓ Market clock status
- ✓ Position fetching
- ✓ Asset information
- ✓ Latest trade data
- ✓ Credential validation

The test suite:
1. Runs all paper trading tests automatically
2. Skips live trading tests by default (use `--run-live` to enable)
3. Displays detailed results for each test
4. Provides a summary of passed/failed/skipped tests

## Integration with LiveExecutor

Use the Alpaca broker with the LiveExecutor:

```python
from executors.live import LiveExecutor
from brokers.alpaca_api import AlpacaBrokerAPI
from contracts.portfolio import Portfolio

# Initialize broker
broker = AlpacaBrokerAPI(paper_trading=True)

# Create portfolio
portfolio = Portfolio(initial_cash=100000)

# Create live executor
executor = LiveExecutor(
    portfolio=portfolio,
    broker_api=broker
)

# Submit orders through executor
order = Order(
    ticker="AAPL",
    quantity=10,
    side=OrderSide.BUY,
    order_type=OrderType.MARKET
)
order_id = executor.submit_order(order)

# Sync portfolio with broker
executor.sync_portfolio()
```

## API Methods

### Connection & Validation
- `test_connection()` - Test API connection
- `validate_credentials()` - Validate API credentials and get account status

### Account Management
- `get_account()` - Get account information (cash, buying power, equity)
- `get_positions()` - Get all current positions
- `get_clock()` - Get market clock (open/closed status)

### Order Management
- `submit_order(order)` - Submit a new order
- `cancel_order(order_id)` - Cancel an existing order
- `get_order_status(order_id)` - Get order status
- `get_fill_info(order_id)` - Get fill information for an order

### Market Data
- `get_asset(symbol)` - Get asset information
- `get_latest_trade(symbol)` - Get latest trade for a symbol
- `stream_quotes(symbols, on_quote)` - Stream real-time quotes (websocket)

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALPACA_API_KEY` | Your Alpaca API key | Required |
| `ALPACA_API_SECRET` | Your Alpaca API secret | Required |
| `ALPACA_PAPER_BASE_URL` | Paper trading API URL | `https://paper-api.alpaca.markets` |
| `ALPACA_LIVE_BASE_URL` | Live trading API URL | `https://api.alpaca.markets` |
| `ALPACA_DATA_URL` | Market data API URL | `https://data.alpaca.markets` |

### Initialization Parameters

```python
AlpacaBrokerAPI(
    config_path=None,        # Path to .env file (optional)
    log_level=logging.INFO,  # Logging level
    paper_trading=True       # True for paper, False for live
)
```

## Best Practices

### Paper Trading
- Always test strategies in paper trading first
- Paper trading uses simulated fills and may not reflect real market conditions
- Use paper trading to validate order logic and strategy behavior

### Live Trading
- Start with small position sizes
- Monitor for trading blocks or account restrictions
- Implement proper risk management and guardrails
- Be aware of pattern day trader rules
- Test thoroughly in paper trading before going live

### Error Handling
```python
try:
    broker = AlpacaBrokerAPI(paper_trading=True)
    account = broker.get_account()
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"API error: {e}")
```

### Logging
```python
import logging

# Set logging level
broker = AlpacaBrokerAPI(
    paper_trading=True,
    log_level=logging.DEBUG  # More verbose logging
)
```

## Troubleshooting

### Common Issues

**"Missing Alpaca API credentials"**
- Ensure `.env` file exists with `ALPACA_API_KEY` and `ALPACA_API_SECRET`
- Check that environment variables are properly loaded

**"Connection test failed"**
- Verify API keys are correct
- Check internet connection
- Ensure you're using the correct base URL for paper/live trading

**"Trading blocked"**
- Check account status in Alpaca dashboard
- Verify account is approved for trading
- Check for pattern day trader restrictions

**"Order submission failed"**
- Verify sufficient buying power
- Check if market is open (for market orders)
- Ensure symbol is tradable
- Validate order parameters (quantity, price, etc.)

### Getting Help

- [Alpaca Documentation](https://alpaca.markets/docs/)
- [Alpaca API Reference](https://alpaca.markets/docs/api-references/trading-api/)
- [Alpaca Community Forum](https://forum.alpaca.markets/)

## Security Notes

- Never commit `.env` file to version control
- Keep API keys secure and private
- Use paper trading keys for development
- Rotate API keys periodically
- Monitor account activity regularly
- Use separate keys for different applications

## Rate Limits

Alpaca has rate limits on API calls:
- 200 requests per minute per API key
- Some endpoints have stricter limits
- The broker API handles basic error responses
- Implement exponential backoff for retries if needed

## Next Steps

1. Complete the [Getting Started](02-getting-started.md) guide
2. Review [Executors](06-executors.md) documentation
3. Explore [Strategies](05-strategies.md) for trading logic
4. Set up [Guardrails](07-guardrails.md) for risk management
