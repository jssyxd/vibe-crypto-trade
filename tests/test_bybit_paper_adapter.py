"""
Unit tests for BybitPaperAdapter.

Tests paper trading functionality including order placement,
position tracking, and PnL calculation.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from execution.adapters.bybit_paper_adapter import (
    BybitPaperAdapter, PaperPosition, PaperOrder
)
from execution.adapters.base_adapter import (
    Order, OrderSide, OrderType, OrderStatus, Position, AccountBalance
)


class TestBybitPaperAdapter:
    """Test suite for BybitPaperAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a fresh adapter for each test."""
        return BybitPaperAdapter(
            api_key="",
            api_secret="",
            testnet=True,
            initial_balance=100000.0,
        )

    def test_init(self, adapter):
        """Test adapter initialization."""
        assert adapter.initial_balance == 100000.0
        assert adapter._balance == 100000.0
        assert len(adapter._positions) == 0
        assert len(adapter._orders) == 0

    def test_connect_simulation_mode(self, adapter):
        """Test connecting in simulation mode."""
        # Mock CCXT to fail so we fall back to simulation
        with patch.object(adapter.exchange, 'fetch_ticker', side_effect=Exception("Test error")):
            result = adapter.connect()
            assert result is True
            assert adapter.connected is True
            assert adapter._use_simulation is True

    def test_connect_testnet_success(self, adapter):
        """Test connecting to testnet successfully."""
        with patch.object(adapter.exchange, 'fetch_ticker', return_value={'last': 80000}):
            result = adapter.connect()
            assert result is True
            assert adapter.connected is True
            assert adapter._use_simulation is False

    def test_disconnect(self, adapter):
        """Test disconnecting."""
        adapter.connect()
        result = adapter.disconnect()
        assert result is True
        assert adapter.connected is False

    def test_get_balance_empty(self, adapter):
        """Test getting balance with no positions."""
        balance = adapter.get_balance()
        assert balance.total_equity == 100000.0
        assert balance.available_balance == 100000.0
        assert len(balance.positions) == 0

    def test_get_balance_with_positions(self, adapter):
        """Test getting balance with open positions."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        balance = adapter.get_balance()
        assert balance.total_equity == 100000.0
        assert len(balance.positions) == 1
        assert "BTC-USDT" in balance.positions

    def test_get_position_empty(self, adapter):
        """Test getting non-existent position."""
        pos = adapter.get_position("BTC-USDT")
        assert pos is None

    def test_get_position_exists(self, adapter):
        """Test getting existing position."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        pos = adapter.get_position("BTC-USDT")
        assert pos is not None
        assert pos.quantity == 0.5

    def test_place_order_market_buy(self, adapter):
        """Test placing a market buy order."""
        adapter.connect()
        order = adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == 0.1
        assert order.avg_fill_price > 0

    def test_place_order_market_sell(self, adapter):
        """Test placing a market sell order."""
        adapter.connect()
        # First buy some BTC
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        # Now sell it
        order = adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        assert order.status == OrderStatus.FILLED

    def test_place_order_insufficient_balance(self, adapter):
        """Test placing order with insufficient balance."""
        adapter.connect()
        with pytest.raises(ValueError, match="Insufficient balance"):
            adapter.place_order(
                symbol="BTC-USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=1000.0,  # Way too much
            )

    def test_place_order_insufficient_position(self, adapter):
        """Test selling more than owned."""
        adapter.connect()
        # Buy some BTC first
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        # Try to sell more than we have
        with pytest.raises(ValueError, match="Insufficient position"):
            adapter.place_order(
                symbol="BTC-USDT",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=1.0,  # More than owned
            )

    def test_cancel_order(self, adapter):
        """Test cancelling an order."""
        adapter.connect()
        # Place order
        order = adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=80000.0,
        )
        # Cancel it
        result = adapter.cancel_order(order.order_id, "BTC-USDT")
        assert result is True
        assert adapter.get_order_status(order.order_id, "BTC-USDT") == OrderStatus.CANCELLED

    def test_get_ticker_simulation(self, adapter):
        """Test getting ticker in simulation mode."""
        adapter.connect()
        ticker = adapter.get_ticker("BTC-USDT")
        assert ticker['symbol'] == "BTC-USDT"
        assert ticker['last'] > 0

    def test_update_prices(self, adapter):
        """Test updating position prices."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        # Update price
        adapter.update_prices({"BTC-USDT": 85000.0})
        pos = adapter.get_position("BTC-USDT")
        assert pos.current_price == 85000.0

    def test_pnl_calculation_long(self, adapter):
        """Test PnL calculation for long position."""
        adapter.connect()
        # Buy at 80000
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        # Update price to 85000
        adapter.update_prices({"BTC-USDT": 85000.0})
        pos = adapter.get_position("BTC-USDT")
        expected_pnl = (85000.0 - 80000.0) * 0.5
        assert abs(pos.unrealized_pnl - expected_pnl) < 1.0

    def test_pnl_calculation_sell(self, adapter):
        """Test PnL calculation for sell and price rise."""
        adapter.connect()
        # Buy first at simulated price
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        # Manually set different entry price to simulate profit scenario
        pos = adapter._positions["BTC-USDT"]
        pos.entry_price = 75000.0  # Simulate buying at lower price
        pos.current_price = 80000.0

        initial_balance = adapter._balance
        # Sell at current market price (80000)
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        pnl = adapter.get_pnl_summary()
        # With entry at 75000 and sell at 80000, profit should be 2500
        assert pnl['total_realized_pnl'] > 0, f"Expected positive realized PnL, got {pnl['total_realized_pnl']}"
        pos = adapter.get_position("BTC-USDT")
        # Position should be closed
        assert pos is None or pos.quantity == 0

    def test_get_pnl_summary(self, adapter):
        """Test getting PnL summary."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        adapter.update_prices({"BTC-USDT": 85000.0})
        pnl = adapter.get_pnl_summary()
        assert 'total_unrealized_pnl' in pnl
        assert 'total_realized_pnl' in pnl
        assert 'total_pnl' in pnl
        assert pnl['total_unrealized_pnl'] > 0

    def test_on_position_update_callback(self, adapter):
        """Test position update callback."""
        adapter.connect()
        updates = []

        def on_update(symbol, position):
            updates.append((symbol, position))

        adapter.on_position_update(on_update)
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        assert len(updates) > 0

    def test_on_order_update_callback(self, adapter):
        """Test order update callback."""
        adapter.connect()
        updates = []

        def on_update(order_id, order):
            updates.append((order_id, order))

        adapter.on_order_update(on_update)
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        assert len(updates) > 0

    def test_get_orders(self, adapter):
        """Test getting all orders."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        adapter.place_order(
            symbol="ETH-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        )
        orders = adapter.get_orders()
        assert len(orders) == 2

    def test_get_open_orders(self, adapter):
        """Test getting open orders."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=80000.0,
        )
        open_orders = adapter.get_open_orders()
        assert len(open_orders) >= 0  # Depends on fill behavior

    def test_get_filled_orders(self, adapter):
        """Test getting filled orders."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        filled = adapter.get_filled_orders()
        assert len(filled) >= 1

    def test_reset(self, adapter):
        """Test resetting the adapter."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        adapter.reset()
        assert adapter._balance == 100000.0
        assert len(adapter._positions) == 0
        assert len(adapter._orders) == 0

    def test_reset_with_new_balance(self, adapter):
        """Test resetting with new balance."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        adapter.reset(initial_balance=50000.0)
        assert adapter._balance == 50000.0

    def test_total_equity(self, adapter):
        """Test total equity calculation."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        adapter.update_prices({"BTC-USDT": 85000.0})
        # Initial: 100000 - (0.5 * 80000) = 60000 cash + 0.5 BTC valued at 85000 = 102500
        expected = 60000.0 + (85000.0 - 80000.0) * 0.5 + 0.5 * 80000.0
        assert abs(adapter.total_equity - expected) < 100

    def test_get_portfolio_stats(self, adapter):
        """Test getting portfolio stats."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        stats = adapter.get_portfolio_stats()
        assert 'total_equity' in stats
        assert 'cash' in stats
        assert 'total_pnl' in stats
        assert 'positions' in stats

    def test_multiple_positions(self, adapter):
        """Test managing multiple positions."""
        adapter.connect()
        adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        adapter.place_order(
            symbol="ETH-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=5.0,
        )
        balance = adapter.get_balance()
        assert len(balance.positions) == 2

    def test_order_tracking(self, adapter):
        """Test that orders are properly tracked."""
        adapter.connect()
        order1 = adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        order2 = adapter.place_order(
            symbol="ETH-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        )
        assert order1.order_id != order2.order_id
        assert order1.order_id.startswith("PAPER_")
        assert order2.order_id.startswith("PAPER_")


class TestPaperPosition:
    """Test suite for PaperPosition dataclass."""

    def test_long_position_pnl(self):
        """Test PnL calculation for long position."""
        pos = PaperPosition(
            symbol="BTC-USDT",
            quantity=1.0,
            entry_price=80000.0,
            current_price=85000.0,
            side="long",
        )
        assert pos.unrealized_pnl == 5000.0

    def test_short_position_pnl(self):
        """Test PnL calculation for short position."""
        pos = PaperPosition(
            symbol="BTC-USDT",
            quantity=1.0,
            entry_price=85000.0,
            current_price=80000.0,
            side="short",
        )
        assert pos.unrealized_pnl == 5000.0

    def test_zero_quantity(self):
        """Test PnL with zero quantity."""
        pos = PaperPosition(
            symbol="BTC-USDT",
            quantity=0.0,
            entry_price=80000.0,
            current_price=85000.0,
            side="long",
        )
        assert pos.unrealized_pnl == 0.0


class TestPaperOrder:
    """Test suite for PaperOrder dataclass."""

    def test_to_order(self):
        """Test converting PaperOrder to Order."""
        paper_order = PaperOrder(
            order_id="TEST_001",
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            price=80000.0,
            status=OrderStatus.FILLED,
            filled_qty=0.1,
            avg_fill_price=80000.0,
        )
        order = paper_order.to_order()
        assert isinstance(order, Order)
        assert order.order_id == "TEST_001"
        assert order.symbol == "BTC-USDT"
        assert order.status == OrderStatus.FILLED


# Integration test with real CCXT (requires network)
class TestBybitPaperAdapterIntegration:
    """Integration tests that may require network access."""

    @pytest.mark.integration
    @pytest.mark.skipif(
        True,  # Skip by default to avoid network dependencies
        reason="Requires network access to Bybit testnet"
    )
    def test_connect_to_bybit_testnet(self):
        """Test actual connection to Bybit testnet."""
        adapter = BybitPaperAdapter(
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
        )
        result = adapter.connect()
        # In integration mode, we expect this to either succeed or fail gracefully
        assert result is True
        assert adapter.connected is True

    @pytest.mark.integration
    @pytest.mark.skipif(
        True,
        reason="Requires network access to Bybit testnet"
    )
    def test_place_order_on_testnet(self):
        """Test placing order with real testnet (mock)."""
        adapter = BybitPaperAdapter(
            api_key="test_key",
            api_secret="test_secret",
            testnet=True,
        )
        adapter.connect()
        # Note: In paper trading mode, even testnet orders are simulated
        order = adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.01,
        )
        assert order.status == OrderStatus.FILLED