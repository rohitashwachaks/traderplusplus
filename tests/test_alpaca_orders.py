"""
Pytest test suite for Alpaca order management.
Tests order submission, cancellation, and status tracking.
"""

import sys
import os
import pytest
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brokers.alpaca_api import AlpacaBrokerAPI
from contracts.order import Order, OrderSide, OrderType, OrderStatus


@pytest.fixture(scope="module")
def paper_broker():
    """Fixture to create a paper trading broker instance."""
    try:
        broker = AlpacaBrokerAPI(paper_trading=True)
        return broker
    except ValueError as e:
        pytest.skip(f"Alpaca credentials not configured: {e}")


@pytest.mark.integration
class TestOrderManagement:
    """Test suite for order management operations."""

    def test_order_creation(self):
        """Test creating an Order object."""
        order = Order(
            ticker="AAPL",
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force="gtc"
        )
        assert order.ticker == "AAPL"
        assert order.quantity == 10
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.time_in_force == "gtc"

    @pytest.mark.skip(reason="Skipping actual order submission to avoid market impact")
    def test_submit_market_order(self, paper_broker):
        """Test submitting a market order (skipped by default)."""
        order = Order(
            ticker="AAPL",
            quantity=1,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force="gtc"
        )
        
        response = paper_broker.submit_order(order)
        assert response is not None
        assert 'id' in response or 'order_id' in response

    @pytest.mark.skip(reason="Skipping actual order operations to avoid market impact")
    def test_get_order_status(self, paper_broker):
        """Test getting order status (skipped by default)."""
        # This would require a valid order_id from a previous submission
        pass

    @pytest.mark.skip(reason="Skipping actual order operations to avoid market impact")
    def test_cancel_order(self, paper_broker):
        """Test canceling an order (skipped by default)."""
        # This would require a valid order_id from a previous submission
        pass


@pytest.mark.integration
class TestPositionManagement:
    """Test suite for position management."""

    def test_get_positions_structure(self, paper_broker):
        """Test that positions are returned in correct format."""
        positions = paper_broker.get_positions()
        assert isinstance(positions, list)
        
        if positions:
            pos = positions[0]
            assert 'symbol' in pos
            assert 'qty' in pos
            assert 'market_value' in pos


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
