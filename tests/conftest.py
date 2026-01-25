"""
Pytest configuration and shared fixtures for Trader++ test suite.
"""

import sys
import os
import pytest
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brokers.alpaca_api import AlpacaBrokerAPI


# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] %(message)s'
)


@pytest.fixture(scope="session")
def paper_broker():
    """
    Session-scoped fixture for paper trading broker.
    Reuses the same broker instance across all tests in a session.
    """
    try:
        broker = AlpacaBrokerAPI(paper_trading=True, log_level=logging.WARNING)
        yield broker
    except ValueError as e:
        pytest.skip(f"Alpaca credentials not configured: {e}")


@pytest.fixture(scope="session")
def live_broker():
    """
    Session-scoped fixture for live trading broker.
    Only used for tests marked with @pytest.mark.live
    """
    try:
        broker = AlpacaBrokerAPI(paper_trading=False, log_level=logging.WARNING)
        yield broker
    except ValueError as e:
        pytest.skip(f"Live trading credentials not configured: {e}")


@pytest.fixture
def test_symbols():
    """Fixture providing common test symbols."""
    return ["AAPL", "MSFT", "GOOGL", "TSLA"]


@pytest.fixture
def sample_order_data():
    """Fixture providing sample order data for testing."""
    return {
        "ticker": "AAPL",
        "quantity": 10,
        "side": "buy",
        "order_type": "market",
        "time_in_force": "gtc"
    }


def pytest_configure(config):
    """
    Pytest configuration hook.
    Called before test collection.
    """
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring API access"
    )
    config.addinivalue_line(
        "markers", "live: mark test as live trading test (requires explicit opt-in)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test with no external dependencies"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to skip live tests by default.
    """
    skip_live = pytest.mark.skip(reason="Live trading tests require --run-live flag")
    
    for item in items:
        if "live" in item.keywords and not config.getoption("--run-live", default=False):
            item.add_marker(skip_live)


def pytest_addoption(parser):
    """
    Add custom command-line options.
    """
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live trading tests (use with caution!)"
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=True,
        help="Run integration tests that require API credentials"
    )
