"""
Unit tests for E2E conftest.py fixtures.

Tests the pytest fixtures defined in tests/e2e/conftest.py.
"""

import pytest
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestE2EProjectRootFixture:
    """Tests for e2e_project_root fixture."""

    def test_e2e_project_root_returns_path(self, e2e_project_root):
        """Test that e2e_project_root returns a valid path."""
        assert e2e_project_root is not None
        assert isinstance(e2e_project_root, Path)
        assert e2e_project_root.exists()


class TestE2EConfigFixture:
    """Tests for e2e_config fixture."""

    def test_e2e_config_has_required_fields(self, e2e_config):
        """Test that e2e_config has all required fields."""
        assert "testnet" in e2e_config
        assert "initial_capital" in e2e_config
        assert "max_position_size" in e2e_config
        assert "max_daily_loss_pct" in e2e_config
        assert "symbols" in e2e_config
        assert "strategies" in e2e_config

    def test_e2e_config_testnet_is_true(self, e2e_config):
        """Test that testnet is set to True."""
        assert e2e_config["testnet"] is True

    def test_e2e_config_symbols_list(self, e2e_config):
        """Test that symbols is a list."""
        assert isinstance(e2e_config["symbols"], list)
        assert "BTC-USDT" in e2e_config["symbols"]


class TestE2EMockExchangeFixture:
    """Tests for e2e_mock_exchange fixture."""

    def test_e2e_mock_exchange_connected(self, e2e_mock_exchange):
        """Test that mock exchange is connected."""
        assert e2e_mock_exchange.connect.called is False  # Not called yet
        result = e2e_mock_exchange.connect()
        assert result is True

    def test_e2e_mock_exchange_has_balance(self, e2e_mock_exchange):
        """Test that mock exchange returns balance."""
        balance = e2e_mock_exchange.get_balance()
        assert balance.total_equity == 100000.0

    def test_e2e_mock_exchange_has_positions(self, e2e_mock_exchange):
        """Test that mock exchange has positions."""
        balance = e2e_mock_exchange.get_balance()
        assert "BTC-USDT" in balance.positions
        assert "ETH-USDT" in balance.positions

    def test_e2e_mock_exchange_ticker(self, e2e_mock_exchange):
        """Test that mock exchange returns tickers."""
        btc_ticker = e2e_mock_exchange.get_ticker("BTC-USDT")
        assert btc_ticker["last"] == 45000.0

        eth_ticker = e2e_mock_exchange.get_ticker("ETH-USDT")
        assert eth_ticker["last"] == 2750.0

    def test_e2e_mock_exchange_place_order(self, e2e_mock_exchange):
        """Test that mock exchange can place orders."""
        order = e2e_mock_exchange.place_order(
            symbol="BTC-USDT",
            side="buy",
            order_type="market",
            quantity=0.1,
        )
        assert order.symbol == "BTC-USDT"
        assert order.quantity == 0.1
        assert order.status.value == "filled"


class TestE2EPortfolioManagerFixture:
    """Tests for e2e_portfolio_manager fixture."""

    def test_e2e_portfolio_manager_initialized(self, e2e_portfolio_manager):
        """Test that portfolio manager is initialized."""
        assert e2e_portfolio_manager is not None
        assert e2e_portfolio_manager.initial_capital == 100000.0

    def test_e2e_portfolio_manager_has_allocations(self, e2e_portfolio_manager):
        """Test that portfolio manager has strategy allocations."""
        allocations = e2e_portfolio_manager._strategy_allocations
        assert len(allocations) == 3
        assert "MA_Cross" in allocations
        assert "RSI_Oversold" in allocations
        assert "Momentum" in allocations


class TestE2ERiskControllerFixture:
    """Tests for e2e_risk_controller fixture."""

    def test_e2e_risk_controller_initialized(self, e2e_risk_controller):
        """Test that risk controller is initialized."""
        assert e2e_risk_controller is not None
        assert e2e_risk_controller.limits is not None

    def test_e2e_risk_controller_check_order(self, e2e_risk_controller):
        """Test that risk controller can check orders."""
        result = e2e_risk_controller.check_order(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0,
            portfolio_value=100000.0,
        )
        assert result.approved is True


class TestE2ESignalQueueFixture:
    """Tests for e2e_signal_queue fixture."""

    def test_e2e_signal_queue_initialized(self, e2e_signal_queue):
        """Test that signal queue is initialized."""
        assert e2e_signal_queue is not None

    def test_e2e_signal_queue_empty_initially(self, e2e_signal_queue):
        """Test that signal queue is empty initially."""
        stats = e2e_signal_queue.get_stats()
        assert stats["total"] == 0


class TestE2ESampleSignalsFixture:
    """Tests for e2e_sample_signals fixture."""

    def test_e2e_sample_signals_is_list(self, e2e_sample_signals):
        """Test that sample signals is a list."""
        assert isinstance(e2e_sample_signals, list)
        assert len(e2e_sample_signals) == 3

    def test_e2e_sample_signals_have_ids(self, e2e_sample_signals):
        """Test that each signal has an ID."""
        for signal in e2e_sample_signals:
            assert signal.signal_id is not None
            assert signal.signal_id.startswith("E2E_SIG_")

    def test_e2e_sample_signals_different_priorities(self, e2e_sample_signals):
        """Test that signals have different priorities."""
        priorities = [s.priority for s in e2e_sample_signals]
        # Should have NORMAL, HIGH, LOW (or similar variety)
        assert len(set(priorities)) >= 2  # At least 2 different priorities


class TestE2EMarketDataFixture:
    """Tests for e2e_market_data fixture."""

    def test_e2e_market_data_has_btc(self, e2e_market_data):
        """Test that market data has BTC."""
        assert "BTC-USDT" in e2e_market_data
        assert e2e_market_data["BTC-USDT"]["last"] == 45000.0

    def test_e2e_market_data_has_eth(self, e2e_market_data):
        """Test that market data has ETH."""
        assert "ETH-USDT" in e2e_market_data
        assert e2e_market_data["ETH-USDT"]["last"] == 2750.0

    def test_e2e_market_data_structure(self, e2e_market_data):
        """Test that market data has all required fields."""
        for symbol, data in e2e_market_data.items():
            assert "last" in data
            assert "bid" in data
            assert "ask" in data
            assert "volume" in data