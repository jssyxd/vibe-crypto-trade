"""
End-to-end test for Bybit paper trading.

Tests the complete paper trading flow including:
- Connection to testnet
- Order placement and execution
- Position tracking
- PnL calculation
- Integration with portfolio and risk management
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from execution.adapters.bybit_paper_adapter import BybitPaperAdapter
from execution.adapters.base_adapter import OrderSide, OrderType, OrderStatus


@pytest.mark.e2e
class TestBybitPaperTrading:
    """E2E tests for Bybit paper trading flow."""

    @pytest.fixture
    def paper_adapter(self):
        """Create a paper trading adapter for E2E tests."""
        adapter = BybitPaperAdapter(
            api_key="test_key_for_e2e",
            api_secret="test_secret_for_e2e",
            testnet=True,
            initial_balance=100000.0,
        )
        adapter.connect()
        return adapter

    @pytest.fixture
    def portfolio_manager(self):
        """Create a portfolio manager for E2E tests."""
        from portfolio.portfolio_manager import PortfolioManager, AllocationStrategy

        pm = PortfolioManager(
            initial_capital=100000.0,
            max_strategies=10,
            allocation_strategy=AllocationStrategy.EQUAL_WEIGHT,
        )
        pm.add_strategy_allocation("MA_Cross", 0.4)
        pm.add_strategy_allocation("RSI_Oversold", 0.3)
        pm.add_strategy_allocation("Momentum", 0.3)
        return pm

    @pytest.fixture
    def risk_controller(self):
        """Create a risk controller for E2E tests."""
        from execution.risk.risk_controller import RiskController, RiskLimits

        limits = RiskLimits(
            max_position_pct=0.1,
            max_leverage=1.0,
            max_drawdown_daily=0.05,
            max_drawdown_weekly=0.10,
            max_drawdown_monthly=0.20,
            max_total_positions=5,
        )
        return RiskController(limits=limits)

    def test_paper_adapter_initialization(self, paper_adapter):
        """Test paper trading adapter initializes correctly."""
        assert paper_adapter is not None
        assert paper_adapter.connected is True
        assert paper_adapter.initial_balance == 100000.0

    def test_paper_trading_buy_flow(self, paper_adapter):
        """
        Test the complete buy flow in paper trading.

        Steps:
        1. Check initial balance
        2. Place a buy order
        3. Verify position is created
        4. Verify balance is updated
        """
        # Initial state
        initial_balance = paper_adapter.get_balance()
        assert initial_balance.total_equity == 100000.0

        # Place buy order
        order = paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        assert order.status == OrderStatus.FILLED

        # Verify balance updated
        new_balance = paper_adapter.get_balance()
        assert new_balance.total_equity == 100000.0  # Equity unchanged (PnL = 0)

        # Verify position exists
        position = paper_adapter.get_position("BTC-USDT")
        assert position is not None
        assert position.quantity == 0.5

    def test_paper_trading_sell_flow(self, paper_adapter):
        """
        Test the complete sell flow in paper trading.

        Steps:
        1. Buy some BTC
        2. Sell part of it
        3. Verify realized PnL
        """
        # Buy first
        buy_order = paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        assert buy_order.status == OrderStatus.FILLED

        # Update price to simulate profit
        paper_adapter.update_prices({"BTC-USDT": 85000.0})

        # Sell
        sell_order = paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        assert sell_order.status == OrderStatus.FILLED

        # Verify position closed
        position = paper_adapter.get_position("BTC-USDT")
        assert position is None or position.quantity == 0

        # Check PnL summary
        pnl = paper_adapter.get_pnl_summary()
        assert pnl['total_realized_pnl'] > 0  # Should have realized profit

    def test_multi_symbol_paper_trading(self, paper_adapter):
        """
        Test trading multiple symbols in paper mode.

        Steps:
        1. Buy BTC
        2. Buy ETH
        3. Verify both positions tracked
        """
        # Buy BTC
        paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.3,
        )

        # Buy ETH
        paper_adapter.place_order(
            symbol="ETH-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=5.0,
        )

        # Verify both positions
        btc_pos = paper_adapter.get_position("BTC-USDT")
        eth_pos = paper_adapter.get_position("ETH-USDT")
        assert btc_pos is not None
        assert eth_pos is not None

        balance = paper_adapter.get_balance()
        assert len(balance.positions) == 2

    def test_pnl_calculation_flow(self, paper_adapter):
        """
        Test PnL calculation as prices change.

        Steps:
        1. Buy at initial price
        2. Update price higher
        3. Verify unrealized PnL increases
        4. Update price lower
        5. Verify unrealized PnL decreases
        """
        # Buy BTC
        paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        )

        initial_pnl = paper_adapter.get_pnl_summary()
        initial_unrealized = initial_pnl['total_unrealized_pnl']

        # Price goes up
        paper_adapter.update_prices({"BTC-USDT": 85000.0})
        up_pnl = paper_adapter.get_pnl_summary()
        assert up_pnl['total_unrealized_pnl'] > initial_unrealized

        # Price goes down
        paper_adapter.update_prices({"BTC-USDT": 75000.0})
        down_pnl = paper_adapter.get_pnl_summary()
        assert down_pnl['total_unrealized_pnl'] < up_pnl['total_unrealized_pnl']

    def test_order_callback_flow(self, paper_adapter):
        """
        Test that order callbacks are triggered correctly.
        """
        order_updates = []

        def on_order_update(order_id, order):
            order_updates.append((order_id, order))

        paper_adapter.on_order_update(on_order_update)

        paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )

        assert len(order_updates) == 1

    def test_position_callback_flow(self, paper_adapter):
        """
        Test that position callbacks are triggered correctly.
        """
        position_updates = []

        def on_position_update(symbol, position):
            position_updates.append((symbol, position))

        paper_adapter.on_position_update(on_position_update)

        paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )

        # Should have at least one position update
        assert len(position_updates) >= 1
        assert position_updates[0][0] == "BTC-USDT"

    def test_portfolio_stats_flow(self, paper_adapter):
        """
        Test getting comprehensive portfolio stats.
        """
        paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        paper_adapter.update_prices({"BTC-USDT": 85000.0})

        stats = paper_adapter.get_portfolio_stats()

        assert 'total_equity' in stats
        assert 'cash' in stats
        assert 'total_pnl' in stats
        assert 'positions' in stats
        assert stats['total_pnl'] > 0

    def test_integration_with_portfolio_manager(
        self, paper_adapter, portfolio_manager
    ):
        """
        Test integration between paper adapter and portfolio manager.

        Steps:
        1. Execute trade on paper adapter
        2. Add position to portfolio
        3. Verify both are in sync
        """
        # Execute trade
        order = paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.3,
        )

        # Add to portfolio manager
        portfolio_manager.add_position(
            strategy_name="MA_Cross",
            symbol="BTC-USDT",
            quantity=0.3,
            entry_price=order.avg_fill_price,
        )

        # Verify
        pm_stats = portfolio_manager.get_portfolio_stats()
        adapter_stats = paper_adapter.get_portfolio_stats()

        assert pm_stats.total_value > 0
        assert adapter_stats.cash < 100000.0

    def test_integration_with_risk_controller(
        self, paper_adapter, risk_controller
    ):
        """
        Test integration between paper adapter and risk controller.

        Steps:
        1. Check risk before order
        2. Execute trade
        3. Verify risk limits still respected
        """
        portfolio_value = paper_adapter.total_equity

        # Check risk for large order - should be rejected or adjusted
        result = risk_controller.check_order(
            symbol="BTC-USDT",
            side="buy",
            quantity=10.0,  # Very large
            price=80000.0,
            portfolio_value=portfolio_value,
        )
        # Risk controller should reject or adjust
        if result.approved:
            assert result.adjustments

    def test_reset_and_start_fresh(self, paper_adapter):
        """
        Test resetting paper trading account.
        """
        # Make some trades
        paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )
        paper_adapter.place_order(
            symbol="ETH-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=5.0,
        )

        # Reset
        paper_adapter.reset()

        # Verify clean state
        balance = paper_adapter.get_balance()
        assert balance.total_equity == 100000.0
        assert len(balance.positions) == 0

        pnl = paper_adapter.get_pnl_summary()
        assert pnl['total_unrealized_pnl'] == 0.0
        assert pnl['total_realized_pnl'] == 0.0

    def test_full_trading_cycle(self, paper_adapter):
        """
        Test a complete trading cycle from start to finish.
        """
        # 1. Start with initial state
        initial_equity = paper_adapter.total_equity
        assert initial_equity == 100000.0

        # 2. Execute multiple trades
        btc_order = paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.2,
        )
        assert btc_order.status == OrderStatus.FILLED

        eth_order = paper_adapter.place_order(
            symbol="ETH-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=3.0,
        )
        assert eth_order.status == OrderStatus.FILLED

        # 3. Update prices
        paper_adapter.update_prices({
            "BTC-USDT": 85000.0,
            "ETH-USDT": 3200.0,
        })

        # 4. Verify PnL
        pnl = paper_adapter.get_pnl_summary()
        assert pnl['total_unrealized_pnl'] > 0

        # 5. Sell BTC for profit
        paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.2,
        )

        # 6. Check final state
        final_pnl = paper_adapter.get_pnl_summary()
        assert final_pnl['total_realized_pnl'] > 0

        # 7. Final stats
        final_stats = paper_adapter.get_portfolio_stats()
        assert final_stats['total_pnl'] != 0

    @pytest.mark.slow
    def test_high_frequency_paper_trading(self, paper_adapter):
        """
        Test high frequency trading in paper mode.

        This simulates rapid trading to ensure adapter
        can handle many orders without issues.
        """
        for i in range(10):
            paper_adapter.place_order(
                symbol="BTC-USDT" if i % 2 == 0 else "ETH-USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=0.01,
            )

        orders = paper_adapter.get_orders()
        assert len(orders) >= 10

        balance = paper_adapter.get_balance()
        assert balance.total_equity > 0

    def test_error_handling_insufficient_balance(self, paper_adapter):
        """
        Test that adapter properly handles insufficient balance.
        """
        with pytest.raises(ValueError, match="Insufficient balance"):
            paper_adapter.place_order(
                symbol="BTC-USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=1000.0,  # Way too much
            )

    def test_error_handling_insufficient_position(self, paper_adapter):
        """
        Test that adapter properly handles insufficient position.
        """
        # Buy some BTC
        paper_adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )

        # Try to sell more than we have
        with pytest.raises(ValueError, match="Insufficient position"):
            paper_adapter.place_order(
                symbol="BTC-USDT",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=1.0,
            )

    def test_simulation_fallback(self):
        """
        Test that adapter falls back to simulation when testnet unavailable.
        """
        adapter = BybitPaperAdapter(
            api_key="",
            api_secret="",
            testnet=True,
        )

        # Mock CCXT to fail
        with patch.object(adapter.exchange, 'fetch_ticker', side_effect=Exception("Network error")):
            result = adapter.connect()
            assert result is True
            assert adapter._use_simulation is True
            assert adapter.connected is True

        # Should still work in simulation mode
        order = adapter.place_order(
            symbol="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        assert order.status == OrderStatus.FILLED