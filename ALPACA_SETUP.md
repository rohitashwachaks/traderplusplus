# Alpaca Integration Setup Guide

Quick setup guide for integrating Alpaca with Trader++.

## Prerequisites

- Python 3.8+
- Alpaca account (sign up at [alpaca.markets](https://alpaca.markets/))

## Step 1: Get API Keys

### For Paper Trading (Recommended)
1. Log in to [Alpaca Paper Trading Dashboard](https://app.alpaca.markets/paper/dashboard/overview)
2. Navigate to "Your API Keys" section
3. Generate new API keys or use existing ones
4. Copy both the **API Key ID** and **Secret Key**

### For Live Trading (Optional)
1. Complete account verification
2. Log in to [Alpaca Live Trading Dashboard](https://app.alpaca.markets/live/dashboard/overview)
3. Generate API keys from the dashboard
4. **⚠️ Warning:** Live trading uses real money. Test thoroughly in paper trading first!

## Step 2: Configure Environment

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your credentials:**
   ```bash
   # Open in your preferred editor
   nano .env
   # or
   vim .env
   # or
   code .env
   ```

3. **Add your API keys:**
   ```bash
   ALPACA_API_KEY=your_actual_api_key_here
   ALPACA_API_SECRET=your_actual_secret_key_here
   ```

4. **Save and close the file**

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

Or if you prefer using pip3:
```bash
pip3 install -r requirements.txt
```

## Step 4: Validate Connection

Run the test suite to validate your setup:

```bash
pytest tests/test_alpaca_connection.py -v
```

Expected output:
```
================================================================================
  ALPACA CONNECTION VALIDATOR
================================================================================

Initializing Alpaca API (Paper Trading)...
✓ Broker initialized

Testing connection...
✓ Connection successful

Validating credentials...
✓ Credentials validated

--------------------------------------------------------------------------------
ACCOUNT SUMMARY
--------------------------------------------------------------------------------
  Account Number:    PA311UAK8N8C
  Status:            ACTIVE
  Cash:              $100,000.00
  Buying Power:      $200,000.00
  Equity:            $100,000.00
  Trading Blocked:   False
  Account Blocked:   False
  Pattern Day Trader: False
  Paper Trading:     True
--------------------------------------------------------------------------------

Checking market status...
✓ Market is currently CLOSED
  Next open:  2026-01-26T09:30:00-05:00
  Next close: 2026-01-26T16:00:00-05:00

Testing asset lookup (AAPL)...
✓ Asset found: Apple Inc. Common Stock
  Tradable: True

Fetching latest trade data (AAPL)...
✓ Latest price: $247.99

================================================================================
  ✓ ALL VALIDATION CHECKS PASSED!
  Your Alpaca integration is ready to use.
================================================================================
```

## Step 5: Run Comprehensive Tests (Optional)

For more detailed testing:

```bash
# Run all tests
pytest tests/ -v

# Run only connection tests
pytest tests/test_alpaca_connection.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term
```

This will:
- Test all paper trading endpoints
- Validate credentials and connections
- Provide detailed results for each test

## Quick Start Example

Once validated, you can use the integration in your code:

```python
from brokers.alpaca_api import AlpacaBrokerAPI
from contracts.order import Order, OrderSide, OrderType

# Initialize broker (paper trading)
broker = AlpacaBrokerAPI(paper_trading=True)

# Get account info
account = broker.get_account()
print(f"Buying Power: ${account['buying_power']}")

# Check market status
clock = broker.get_clock()
print(f"Market is {'OPEN' if clock['is_open'] else 'CLOSED'}")

# Create and submit an order (paper trading)
order = Order(
    ticker="AAPL",
    quantity=10,
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    time_in_force="gtc"
)

order_id = broker.submit_order(order)
print(f"Order submitted: {order_id}")
```

## Troubleshooting

### "Missing Alpaca API credentials"
- Ensure `.env` file exists in the project root
- Verify `ALPACA_API_KEY` and `ALPACA_API_SECRET` are set
- Check for typos in the environment variable names

### "Connection test failed"
- Verify API keys are correct (no extra spaces)
- Check internet connection
- Ensure you're using paper trading keys with paper trading mode
- Try regenerating API keys in Alpaca dashboard

### "Trading blocked" or "Account blocked"
- Check account status in Alpaca dashboard
- Verify account is approved for trading
- For live trading, ensure account funding is complete

### Import errors
- Run `pip install -r requirements.txt` again
- Ensure you're using Python 3.8 or higher
- Check that you're in the correct virtual environment (if using one)

## Security Best Practices

✓ **DO:**
- Keep your `.env` file private (it's in `.gitignore`)
- Use paper trading for development and testing
- Rotate API keys periodically
- Use separate keys for different applications

✗ **DON'T:**
- Commit `.env` to version control
- Share API keys publicly
- Use live trading keys in development
- Hard-code credentials in your code

## Next Steps

1. ✓ Complete setup and validation
2. Read the [Alpaca Integration Guide](docs/11-alpaca-integration.md)
3. Review [Executors Documentation](docs/06-executors.md)
4. Explore [Strategy Examples](strategies/)
5. Set up [Guardrails](docs/07-guardrails.md) for risk management

## Resources

- [Alpaca Documentation](https://alpaca.markets/docs/)
- [Alpaca API Reference](https://alpaca.markets/docs/api-references/trading-api/)
- [Alpaca Community Forum](https://forum.alpaca.markets/)
- [Trader++ Documentation](docs/)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the [detailed integration guide](docs/11-alpaca-integration.md)
3. Check Alpaca's status page for API issues
4. Review logs for detailed error messages

---

**Ready to trade?** Start with paper trading and test your strategies thoroughly before considering live trading!
