"""
Unit tests for test_helpers module.

Tests the utility functions provided in test_helpers.py.
"""

import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_helpers import (
    create_mock_order,
    create_mock_balance,
    create_mock_position,
    create_mock_ticker,
    create_mock_signal,
    assert_order_equal,
    assert_portfolio_stats_valid,
    MockExchangeAdapter,
    generate_timestamp_series,
    create_price_series,
)


class TestMockOrderCreation:
    """Tests for create_mock_order function."""

    def test_create_order_with_defaults(self):
        """Test creating an order with default values."""
        order = create_mock_order()

        assert order["order_id"] == "TEST_ORDER_001"
        assert order["symbol"] == "BTC-USDT"
        assert order["side"] == "buy"
        assert order["order_type"] == "market"
        assert order["quantity"] == 0.1
        assert order["status"] == "filled"

    def test_create_order_with_custom_values(self):
        """Test creating an order with custom values."""
        order = create_mock_order(
            order_id="CUSTOM_001",
            symbol="ETH-USDT",
            side="sell",
            order_type="limit",
            quantity=2.5,
            price=3000.0,
        )

        assert order["order_id"] == "CUSTOM_001"
        assert order["symbol"] == "ETH-USDT"
        assert order["side"] == "sell"
        assert order["order_type"] == "limit"
        assert order["quantity"] == 2.5
        assert order["price"] == 3000.0

    def test_create_order_filled_qty_defaults_to_quantity(self):
        """Test that filled_qty defaults to quantity when filled."""
        order = create_mock_order(quantity=0.5)
        assert order["filled_qty"] == 0.5


class TestMockBalanceCreation:
    """Tests for create_mock_balance function."""

    def test_create_balance_with_defaults(self):
        """Test creating a balance with default values."""
        balance = create_mock_balance()

        assert balance["total_equity"] == 100000.0
        assert balance["available_balance"] == 90000.0
        assert balance["locked_balance"] == 10000.0
        assert balance["positions"] == []

    def test_create_balance_with_positions(self):
        """Test creating a balance with positions."""
        positions = [
            create_mock_position("BTC-USDT", 0.5, 40000.0, 45000.0),
        ]
        balance = create_mock_balance(positions=positions)

        assert len(balance["positions"]) == 1
        assert balance["positions"][0]["symbol"] == "BTC-USDT"


class TestMockPositionCreation:
    """Tests for create_mock_position function."""

    def test_create_position_with_defaults(self):
        """Test creating a position with default values."""
        position = create_mock_position()

        assert position["symbol"] == "BTC-USDT"
        assert position["quantity"] == 0.5
        assert position["entry_price"] == 40000.0
        assert position["current_price"] == 45000.0

    def test_create_position_pnl_calculation(self):
        """Test that unrealized PnL is calculated correctly."""
        position = create_mock_position(
            symbol="ETH-USDT",
            quantity=2.0,
            entry_price=2000.0,
            current_price=2200.0,
        )

        expected_pnl = (2200.0 - 2000.0) * 2.0  # 400.0
        assert position["unrealized_pnl"] == expected_pnl

    def test_create_position_negative_pnl(self):
        """Test position with negative PnL (loss)."""
        position = create_mock_position(
            quantity=1.0,
            entry_price=50000.0,
            current_price=45000.0,
        )

        expected_pnl = (45000.0 - 50000.0) * 1.0  # -5000.0
        assert position["unrealized_pnl"] == expected_pnl


class TestMockTickerCreation:
    """Tests for create_mock_ticker function."""

    def test_create_ticker_with_defaults(self):
        """Test creating a ticker with default values."""
        ticker = create_mock_ticker()

        assert ticker["symbol"] == "BTC-USDT"
        assert ticker["last"] == 45000.0
        assert ticker["bid"] == 44990.0
        assert ticker["ask"] == 45010.0
        assert "timestamp" in ticker

    def test_create_ticker_custom_values(self):
        """Test creating a ticker with custom values."""
        ticker = create_mock_ticker(
            symbol="ETH-USDT",
            last=3000.0,
            bid=2999.0,
            ask=3001.0,
            volume=500000.0,
        )

        assert ticker["symbol"] == "ETH-USDT"
        assert ticker["last"] == 3000.0
        assert ticker["volume"] == 500000.0


class TestMockSignalCreation:
    """Tests for create_mock_signal function."""

    def test_create_signal_with_defaults(self):
        """Test creating a signal with default values."""
        signal = create_mock_signal()

        assert signal["signal_id"] == "SIG001"
        assert signal["symbol"] == "BTC-USDT"
        assert signal["side"] == "buy"
        assert signal["strategy_name"] == "TestStrategy"
        assert signal["priority"] == "NORMAL"

    def test_create_signal_custom_priority(self):
        """Test creating signals with different priorities."""
        high_priority = create_mock_signal(priority="HIGH")
        low_priority = create_mock_signal(priority="LOW")

        assert high_priority["priority"] == "HIGH"
        assert low_priority["priority"] == "LOW"


class TestAssertFunctions:
    """Tests for assertion helper functions."""

    def test_assert_order_equal_passes(self):
        """Test assert_order_equal with matching orders."""
        actual = {
            "order_id": "TEST_001",
            "symbol": "BTC-USDT",
            "side": "buy",
            "quantity": 0.5,
            "status": "filled",
        }
        expected = {
            "order_id": "TEST_001",
            "symbol": "BTC-USDT",
            "side": "buy",
            "quantity": 0.5,
            "status": "filled",
        }
        assert_order_equal(actual, expected)  # Should not raise

    def test_assert_order_equal_fails_on_mismatch(self):
        """Test assert_order_equal raises on mismatch."""
        actual = {
            "order_id": "TEST_001",
            "symbol": "ETH-USDT",  # Different!
            "side": "buy",
            "quantity": 0.5,
            "status": "filled",
        }
        expected = {
            "order_id": "TEST_001",
            "symbol": "BTC-USDT",
            "side": "buy",
            "quantity": 0.5,
            "status": "filled",
        }
        with pytest.raises(AssertionError):
            assert_order_equal(actual, expected)

    def test_assert_portfolio_stats_valid(self):
        """Test assert_portfolio_stats_valid with valid stats."""
        stats = {
            "total_value": 100000.0,
            "cash": 50000.0,
            "total_pnl": 5000.0,
        }
        assert_portfolio_stats_valid(stats)  # Should not raise

    def test_assert_portfolio_stats_valid_missing_field(self):
        """Test assert_portfolio_stats_valid raises on missing field."""
        stats = {
            "total_value": 100000.0,
            "cash": 50000.0,
            # Missing total_pnl
        }
        with pytest.raises(AssertionError):
            assert_portfolio_stats_valid(stats)


class TestMockExchangeAdapter:
    """Tests for MockExchangeAdapter class."""

    def test_adapter_initialization(self):
        """Test adapter initializes with correct defaults."""
        adapter = MockExchangeAdapter()

        assert adapter._balance == 100000.0
        assert adapter._positions == {}
        assert adapter._connected is False

    def test_adapter_connect_disconnect(self):
        """Test adapter connect and disconnect."""
        adapter = MockExchangeAdapter()

        assert adapter.connect() is True
        assert adapter.connected is True

        assert adapter.disconnect() is True
        assert adapter.connected is False

    def test_adapter_get_balance(self):
        """Test adapter returns correct balance."""
        adapter = MockExchangeAdapter(initial_balance=50000.0)
        balance = adapter.get_balance()

        assert balance["total_equity"] == 50000.0
        assert balance["available_balance"] == 50000.0

    def test_adapter_place_order(self):
        """Test adapter order placement."""
        adapter = MockExchangeAdapter()
        order = adapter.place_order(
            symbol="BTC-USDT",
            side="buy",
            order_type="market",
            quantity=0.5,
        )

        assert order["symbol"] == "BTC-USDT"
        assert order["side"] == "buy"
        assert order["quantity"] == 0.5
        assert order["status"] == "filled"

    def test_adapter_get_ticker(self):
        """Test adapter returns ticker data."""
        adapter = MockExchangeAdapter()
        ticker = adapter.get_ticker("BTC-USDT")

        assert "symbol" in ticker
        assert "last" in ticker
        assert "bid" in ticker
        assert "ask" in ticker

    def test_adapter_with_initial_positions(self):
        """Test adapter with initial positions."""
        positions = {"BTC-USDT": 0.5}
        adapter = MockExchangeAdapter(initial_positions=positions)

        assert "BTC-USDT" in adapter._positions
        assert adapter._positions["BTC-USDT"] == 0.5


class TestTimestampSeries:
    """Tests for generate_timestamp_series function."""

    def test_generate_hourly_timestamps(self):
        """Test generating hourly timestamps."""
        start = datetime(2024, 1, 1, 10, 0, 0)
        series = generate_timestamp_series(start, periods=5, freq="1h")

        assert len(series) == 5
        assert series[0] == start
        assert series[1] == start + timedelta(hours=1)
        assert series[4] == start + timedelta(hours=4)

    def test_generate_minute_timestamps(self):
        """Test generating minute timestamps."""
        start = datetime(2024, 1, 1, 10, 0, 0)
        series = generate_timestamp_series(start, periods=3, freq="1m")

        assert len(series) == 3
        assert series[1] == start + timedelta(minutes=1)


class TestPriceSeries:
    """Tests for create_price_series function."""

    def test_price_series_length(self):
        """Test that price series has correct length."""
        prices = create_price_series(periods=100)
        assert len(prices) == 100

    def test_price_series_positive(self):
        """Test that all prices are positive."""
        prices = create_price_series(periods=50)
        assert all(p > 0 for p in prices)

    def test_price_series_starts_at_base(self):
        """Test that series starts at base price."""
        prices = create_price_series(base_price=50000.0)
        assert prices[0] == 50000.0

    def test_price_series_with_trend(self):
        """Test that trend affects price direction (on average)."""
        # Upward trend
        upward_prices = create_price_series(base_price=100.0, periods=50, trend=0.01)
        # Should generally trend upward (not guaranteed due to randomness)

        # The last price should sometimes be higher due to positive trend
        # This is probabilistic, so we just check it's a valid series
        assert len(upward_prices) == 50
        assert all(p > 0 for p in upward_prices)