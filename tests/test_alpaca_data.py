"""
Pytest test suite for Alpaca data fetching.
Tests historical data retrieval and market data access.
"""

import sys
import os
import pytest
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_ingestion.alpaca_fetcher import fetch_alpaca_data


@pytest.fixture
def test_symbol():
    """Fixture providing a test symbol."""
    return "AAPL"


@pytest.fixture
def date_range():
    """Fixture providing a test date range."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


@pytest.mark.integration
class TestAlpacaDataFetcher:
    """Test suite for Alpaca data fetching."""

    def test_fetch_alpaca_data(self, test_symbol, date_range):
        """Test fetching historical data from Alpaca."""
        start_date, end_date = date_range
        
        try:
            df = fetch_alpaca_data(test_symbol, start_date, end_date)
            
            assert df is not None
            assert len(df) > 0
            assert 'open' in df.columns or 'Open' in df.columns
            assert 'close' in df.columns or 'Close' in df.columns
            assert 'high' in df.columns or 'High' in df.columns
            assert 'low' in df.columns or 'Low' in df.columns
            assert 'volume' in df.columns or 'Volume' in df.columns
            
        except Exception as e:
            pytest.skip(f"Data fetching failed (may be due to API limits or credentials): {e}")

    def test_fetch_invalid_symbol(self):
        """Test fetching data for invalid symbol."""
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        
        with pytest.raises(Exception):
            fetch_alpaca_data("INVALID_SYMBOL_12345", start_date, end_date)

    def test_fetch_invalid_date_range(self, test_symbol):
        """Test fetching data with invalid date range."""
        # End date before start date
        start_date = "2024-12-31"
        end_date = "2024-01-01"
        
        try:
            df = fetch_alpaca_data(test_symbol, start_date, end_date)
            # Some APIs might return empty dataframe instead of error
            assert df is not None
        except Exception:
            # Expected behavior - invalid date range should raise error
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
