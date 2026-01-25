# Tests

Pytest-based test suite for the Trader++ trading framework.

## Overview

The test suite uses pytest for test discovery, execution, and reporting. Tests are organized into modules by functionality:

- `test_alpaca_connection.py` - Connection and credential validation tests
- `test_alpaca_orders.py` - Order management and execution tests
- `test_alpaca_data.py` - Data fetching and market data tests

## Installation

Install pytest and dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_alpaca_connection.py
```

### Run Specific Test Class

```bash
pytest tests/test_alpaca_connection.py::TestAlpacaConnection
```

### Run Specific Test Function

```bash
pytest tests/test_alpaca_connection.py::TestAlpacaConnection::test_connection
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Detailed Output

```bash
pytest -vv
```

### Run and Show Print Statements

```bash
pytest -s
```

## Test Markers

Tests are organized using pytest markers:

### Integration Tests

Tests that require API credentials and make real API calls:

```bash
# Run only integration tests
pytest -m integration

# Skip integration tests
pytest -m "not integration"
```

### Live Trading Tests

Tests that interact with live trading (skipped by default):

```bash
# Run live trading tests (use with caution!)
pytest --run-live

# Run only live tests
pytest -m live --run-live
```

### Unit Tests

Tests with no external dependencies:

```bash
pytest -m unit
```

### Slow Tests

Tests that take longer to execute:

```bash
# Skip slow tests
pytest -m "not slow"
```

## Test Fixtures

Shared fixtures are defined in `conftest.py`:

- `paper_broker` - Session-scoped paper trading broker instance
- `live_broker` - Session-scoped live trading broker instance
- `test_symbols` - Common test symbols (AAPL, MSFT, etc.)
- `sample_order_data` - Sample order data for testing

## Configuration

Test configuration is in `pytest.ini` at the project root:

- Test discovery patterns
- Custom markers
- Output formatting
- Logging configuration

## Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Get Alpaca API keys:**
   - Paper trading: [Alpaca Paper Dashboard](https://app.alpaca.markets/paper/dashboard/overview)
   - Live trading: [Alpaca Live Dashboard](https://app.alpaca.markets/live/dashboard/overview)

## Test Coverage

To run tests with coverage reporting (requires pytest-cov):

```bash
# Install pytest-cov
pip install pytest-cov

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

## Common Test Scenarios

### Quick Validation

Test that your Alpaca credentials are working:

```bash
pytest tests/test_alpaca_connection.py::TestAlpacaConnection::test_connection -v
```

### Test Account Access

```bash
pytest tests/test_alpaca_connection.py::TestAlpacaConnection::test_get_account -v
```

### Test Market Data

```bash
pytest tests/test_alpaca_connection.py::TestAlpacaConnection::test_get_latest_trade -v
```

### Run All Connection Tests

```bash
pytest tests/test_alpaca_connection.py -v
```

## Continuous Integration

For CI/CD pipelines:

```bash
# Run tests with JUnit XML output
pytest --junitxml=test-results.xml

# Run with coverage and XML output
pytest --cov=. --cov-report=xml --junitxml=test-results.xml
```

## Troubleshooting

### Tests Skipped

If tests are skipped with "Alpaca credentials not configured":
1. Verify `.env` file exists
2. Check `ALPACA_API_KEY` and `ALPACA_API_SECRET` are set
3. Ensure no typos in environment variable names

### Connection Failures

If connection tests fail:
1. Verify API keys are correct
2. Check internet connection
3. Ensure you're using paper trading keys with paper trading tests
4. Check Alpaca API status: https://status.alpaca.markets/

### Import Errors

If you see "ModuleNotFoundError":
1. Ensure you're running pytest from the project root
2. Check that `pytest.ini` has `pythonpath = .`
3. Verify all dependencies are installed

### Live Trading Tests

Live trading tests are **skipped by default** for safety. To run them:

```bash
pytest --run-live -m live
```

⚠️ **Warning:** Live trading tests use real money. Only run with small amounts and in controlled environments.

## Writing New Tests

### Basic Test Structure

```python
import pytest
from brokers.alpaca_api import AlpacaBrokerAPI

class TestMyFeature:
    def test_something(self, paper_broker):
        """Test description."""
        result = paper_broker.some_method()
        assert result is not None
```

### Using Markers

```python
@pytest.mark.integration
def test_api_call(paper_broker):
    """Test that requires API access."""
    pass

@pytest.mark.live
def test_live_trading(live_broker):
    """Test for live trading (skipped by default)."""
    pass

@pytest.mark.slow
def test_long_running():
    """Test that takes a long time."""
    pass
```

### Using Fixtures

```python
def test_with_symbols(test_symbols):
    """Test using the test_symbols fixture."""
    for symbol in test_symbols:
        # Test logic here
        pass
```

## Best Practices

1. **Use descriptive test names** - Test names should clearly describe what is being tested
2. **One assertion per test** - Keep tests focused and simple
3. **Use fixtures** - Reuse common setup code via fixtures
4. **Mark appropriately** - Use markers to categorize tests
5. **Clean up resources** - Use fixtures with yield for setup/teardown
6. **Avoid test interdependencies** - Tests should be independent
7. **Mock external calls** - Use mocks for unit tests to avoid API calls

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Pytest Markers](https://docs.pytest.org/en/stable/mark.html)
- [Alpaca API Documentation](https://alpaca.markets/docs/)

## Support

For issues with:
- **Tests:** Check this README and pytest documentation
- **Alpaca Integration:** See [Alpaca Setup Guide](../ALPACA_SETUP.md)
- **API Issues:** Check [Alpaca Status](https://status.alpaca.markets/)

---

**Happy Testing!** 🧪
