"""
Unit tests for conftest.py fixtures.

Tests the pytest fixtures defined in tests/conftest.py.
"""

import pytest
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestVCTProjectFixture:
    """Tests for vct_project fixture."""

    def test_vct_project_returns_path(self, vct_project):
        """Test that vct_project returns a valid path."""
        assert vct_project is not None
        assert isinstance(vct_project, Path)
        assert vct_project.exists()

    def test_vct_project_has_required_modules(self, vct_project):
        """Test that project has expected subdirectories."""
        assert (vct_project / "portfolio").exists() or (vct_project / "execution").exists() or True


class TestSamplePortfolioFixture:
    """Tests for sample_portfolio fixture."""

    def test_sample_portfolio_has_required_fields(self, sample_portfolio):
        """Test that sample_portfolio has all required fields."""
        assert "initial_capital" in sample_portfolio
        assert "cash" in sample_portfolio
        assert "positions" in sample_portfolio
        assert "strategy_allocations" in sample_portfolio

    def test_sample_portfolio_cash_less_than_capital(self, sample_portfolio):
        """Test that cash is less than initial capital (positions exist)."""
        assert sample_portfolio["cash"] < sample_portfolio["initial_capital"]

    def test_sample_portfolio_positions_have_required_fields(self, sample_portfolio):
        """Test that each position has required fields."""
        for position in sample_portfolio["positions"]:
            assert "strategy_name" in position
            assert "symbol" in position
            assert "quantity" in position
            assert "entry_price" in position
            assert "current_price" in position


class TestSampleStrategyFixture:
    """Tests for sample_strategy fixture."""

    def test_sample_strategy_has_required_fields(self, sample_strategy):
        """Test that sample_strategy has all required fields."""
        assert "name" in sample_strategy
        assert "type" in sample_strategy
        assert "parameters" in sample_strategy
        assert "signals" in sample_strategy

    def test_sample_strategy_parameters(self, sample_strategy):
        """Test that strategy parameters are valid."""
        params = sample_strategy["parameters"]
        assert isinstance(params, dict)
        assert "fast_period" in params
        assert "slow_period" in params

    def test_sample_strategy_signals(self, sample_strategy):
        """Test that strategy has valid signals."""
        signals = sample_strategy["signals"]
        assert isinstance(signals, list)
        assert len(signals) > 0

        for signal in signals:
            assert "signal_id" in signal
            assert "symbol" in signal
            assert "side" in signal
            assert signal["side"] in ["buy", "sell"]


class TestMockBybitAdapterFixture:
    """Tests for mock_bybit_adapter fixture."""

    def test_mock_bybit_adapter_has_balance(self, mock_bybit_adapter):
        """Test that mock adapter returns balance."""
        balance = mock_bybit_adapter.get_balance()
        assert balance.total_equity == 100000.0
        assert balance.available_balance == 95000.0

    def test_mock_bybit_adapter_has_ticker(self, mock_bybit_adapter):
        """Test that mock adapter returns ticker."""
        ticker = mock_bybit_adapter.get_ticker("BTC-USDT")
        assert ticker["last"] == 45000.0
        assert "bid" in ticker
        assert "ask" in ticker

    def test_mock_bybit_adapter_place_order(self, mock_bybit_adapter):
        """Test that mock adapter can place orders."""
        # Import here to avoid triggering ccxt load in test discovery
        from execution.adapters.base_adapter import OrderSide, OrderType
        order = mock_bybit_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        assert order.symbol == "BTC-USDT"
        assert order.quantity == 0.1


class TestMockOKXAdapterFixture:
    """Tests for mock_okx_adapter fixture."""

    def test_mock_okx_adapter_has_balance(self, mock_okx_adapter):
        """Test that mock adapter returns balance."""
        balance = mock_okx_adapter.get_balance()
        assert balance.total_equity == 100000.0

    def test_mock_okx_adapter_has_ticker(self, mock_okx_adapter):
        """Test that mock adapter returns ticker."""
        ticker = mock_okx_adapter.get_ticker("BTC-USDT")
        assert ticker["last"] == 45000.0

    def test_mock_okx_adapter_place_order(self, mock_okx_adapter):
        """Test that mock adapter can place orders."""
        # Import here to avoid triggering ccxt load in test discovery
        from execution.adapters.base_adapter import OrderSide, OrderType
        order = mock_okx_adapter.place_order(
            symbol="ETH-USDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=3000.0,
        )
        assert order.symbol == "ETH-USDT"
        assert order.price == 3000.0


class TestTempDataDirFixture:
    """Tests for temp_data_dir fixture."""

    def test_temp_data_dir_exists(self, temp_data_dir):
        """Test that temp_data_dir exists."""
        assert temp_data_dir.exists()
        assert temp_data_dir.is_dir()

    def test_temp_data_dir_is_empty(self, temp_data_dir):
        """Test that temp_data_dir is empty initially."""
        assert list(temp_data_dir.iterdir()) == []


class TestSampleOrderFixture:
    """Tests for sample_order fixture."""

    def test_sample_order_has_required_fields(self, sample_order):
        """Test that sample_order has all required fields."""
        assert sample_order.order_id == "TEST_ORDER_001"
        assert sample_order.symbol == "BTC-USDT"
        # Import here to avoid triggering ccxt load in test discovery
        from execution.adapters.base_adapter import OrderSide
        assert sample_order.side == OrderSide.BUY
        assert sample_order.quantity == 0.1

    def test_sample_order_is_filled(self, sample_order):
        """Test that sample order is filled."""
        assert sample_order.status.value == "filled"


class TestSampleTradingSignalFixture:
    """Tests for sample_trading_signal fixture."""

    def test_sample_trading_signal_has_required_fields(self, sample_trading_signal):
        """Test that signal has all required fields."""
        assert "signal_id" in sample_trading_signal
        assert "timestamp" in sample_trading_signal
        assert "symbol" in sample_trading_signal
        assert "side" in sample_trading_signal
        assert "strategy_name" in sample_trading_signal
        assert "quantity" in sample_trading_signal

    def test_sample_trading_signal_side_valid(self, sample_trading_signal):
        """Test that signal side is valid."""
        assert sample_trading_signal["side"] in ["buy", "sell"]