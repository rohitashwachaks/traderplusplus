"""
Pytest test suite for Alpaca API connection validation.
Tests paper trading connection without requiring user input.
"""

import sys
import os
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brokers.alpaca_api import AlpacaBrokerAPI


@pytest.fixture(scope="module")
def paper_broker():
    """Fixture to create a paper trading broker instance."""
    try:
        broker = AlpacaBrokerAPI(paper_trading=True)
        return broker
    except ValueError as e:
        pytest.skip(f"Alpaca credentials not configured: {e}")


class TestAlpacaConnection:
    """Test suite for Alpaca API connection."""

    def test_broker_initialization(self, paper_broker):
        """Test that broker initializes successfully."""
        assert paper_broker is not None
        assert paper_broker.paper_trading is True
        assert paper_broker.base_url == "https://paper-api.alpaca.markets"

    def test_connection(self, paper_broker):
        """Test connection to Alpaca API."""
        success, account = paper_broker.test_connection()
        assert success is True
        assert account is not None
        assert 'account_number' in account
        assert 'status' in account

    def test_validate_credentials(self, paper_broker):
        """Test credential validation."""
        validation = paper_broker.validate_credentials()
        assert validation['valid'] is True
        assert 'account_number' in validation
        assert 'status' in validation
        assert validation['status'] == 'ACTIVE'
        assert validation['paper_trading'] is True
        assert validation['trading_blocked'] is False
        assert validation['account_blocked'] is False

    def test_get_account(self, paper_broker):
        """Test fetching account information."""
        account = paper_broker.get_account()
        assert account is not None
        assert 'account_number' in account
        assert 'cash' in account
        assert 'buying_power' in account
        assert 'equity' in account
        assert 'portfolio_value' in account
        assert float(account['cash']) >= 0
        assert float(account['buying_power']) >= 0

    def test_get_clock(self, paper_broker):
        """Test fetching market clock."""
        clock = paper_broker.get_clock()
        assert clock is not None
        assert 'is_open' in clock
        assert 'timestamp' in clock
        assert 'next_open' in clock
        assert 'next_close' in clock
        assert isinstance(clock['is_open'], bool)

    def test_get_positions(self, paper_broker):
        """Test fetching positions."""
        positions = paper_broker.get_positions()
        assert positions is not None
        assert isinstance(positions, list)

    def test_get_asset(self, paper_broker):
        """Test fetching asset information."""
        asset = paper_broker.get_asset("AAPL")
        assert asset is not None
        assert asset['symbol'] == 'AAPL'
        assert 'name' in asset
        assert 'exchange' in asset
        assert 'tradable' in asset
        assert 'class' in asset
        assert asset['tradable'] is True

    def test_get_latest_trade(self, paper_broker):
        """Test fetching latest trade data."""
        trade_data = paper_broker.get_latest_trade("AAPL")
        assert trade_data is not None
        assert 'symbol' in trade_data or 'trade' in trade_data
        
        if 'trade' in trade_data:
            trade = trade_data['trade']
            assert 'p' in trade  # price
            assert float(trade['p']) > 0


class TestAlpacaConnectionErrors:
    """Test suite for error handling."""

    def test_invalid_symbol(self, paper_broker):
        """Test that invalid symbol raises appropriate error."""
        with pytest.raises(Exception):
            paper_broker.get_asset("INVALID_SYMBOL_12345")

    def test_broker_initialization_without_credentials(self, monkeypatch):
        """Test that broker initialization fails without credentials."""
        # Set environment variables to empty strings to simulate missing credentials
        monkeypatch.setenv('ALPACA_API_KEY', '')
        monkeypatch.setenv('ALPACA_API_SECRET', '')
        
        with pytest.raises(ValueError, match="Missing Alpaca API credentials"):
            AlpacaBrokerAPI(paper_trading=True)


@pytest.mark.live
class TestLiveTradingConnection:
    """Test suite for live trading connection (requires explicit opt-in)."""

    @pytest.fixture(scope="class")
    def live_broker(self):
        """Fixture to create a live trading broker instance."""
        try:
            broker = AlpacaBrokerAPI(paper_trading=False)
            return broker
        except ValueError as e:
            pytest.skip(f"Live trading credentials not configured: {e}")

    def test_live_connection(self, live_broker):
        """Test connection to live trading API."""
        success, account = live_broker.test_connection()
        assert success is True
        assert account is not None

    def test_live_credentials(self, live_broker):
        """Test live trading credential validation."""
        validation = live_broker.validate_credentials()
        assert validation['valid'] is True
        assert validation['paper_trading'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
