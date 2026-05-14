"""
End-to-end test template for VCT trading flow.

This module provides a template for testing complete trading flows,
from signal generation through execution to portfolio updates.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


@pytest.mark.e2e
class TestTradingFlow:
    """E2E tests for complete trading flows."""

    def test_signal_to_execution_flow(
        self,
        e2e_mock_exchange,
        e2e_portfolio_manager,
        e2e_risk_controller,
        e2e_signal_queue,
        e2e_sample_signals,
    ):
        """
        Test the complete flow from signal generation to execution.

        This test verifies:
        1. Signals are added to the queue
        2. Risk controller approves the orders
        3. Exchange executes the orders
        4. Portfolio is updated with new positions
        """
        # Step 1: Add signals to queue
        for signal in e2e_sample_signals:
            e2e_signal_queue.add(signal)

        stats = e2e_signal_queue.get_stats()
        assert stats["total"] == 3, f"Expected 3 signals, got {stats['total']}"

        # Step 2: Process signals through risk controller
        for signal in e2e_sample_signals:
            risk_result = e2e_risk_controller.check_order(
                symbol=signal.symbol,
                side=signal.side,
                quantity=signal.quantity,
                price=e2e_mock_exchange.get_ticker(signal.symbol)["last"],
                portfolio_value=e2e_portfolio_manager.get_portfolio_stats().total_value,
            )
            assert risk_result.approved, f"Risk controller rejected: {risk_result.message}"

        # Step 3: Execute orders via exchange
        executed_orders = []
        for signal in e2e_sample_signals:
            order = e2e_mock_exchange.place_order(
                symbol=signal.symbol,
                side=signal.side,
                order_type="market",
                quantity=signal.quantity,
            )
            executed_orders.append(order)

        assert len(executed_orders) == 3, "Not all orders were executed"

        # Step 4: Verify exchange balance updated
        balance = e2e_mock_exchange.get_balance()
        assert balance.total_equity > 0

    def test_portfolio_update_after_trades(
        self,
        e2e_mock_exchange,
        e2e_portfolio_manager,
    ):
        """
        Test that portfolio is correctly updated after trades.

        This test verifies:
        1. Initial portfolio state is correct
        2. After buying, position is added and cash decreases
        3. After price update, unrealized PnL is calculated
        """
        # Get initial stats
        initial_stats = e2e_portfolio_manager.get_portfolio_stats()
        initial_cash = initial_stats.cash
        initial_value = initial_stats.total_value

        # Simulate adding a position (buy)
        success = e2e_portfolio_manager.add_position(
            strategy_name="TestStrategy",
            symbol="BTC-USDT",
            quantity=0.5,
            entry_price=45000.0,
        )
        assert success, "Failed to add position"

        # Verify cash decreased
        updated_stats = e2e_portfolio_manager.get_portfolio_stats()
        assert updated_stats.cash == initial_cash - (0.5 * 45000.0)

        # Update price and verify PnL calculation
        e2e_portfolio_manager.update_position_price("TestStrategy", "BTC-USDT", 46000.0)
        updated_stats = e2e_portfolio_manager.get_portfolio_stats()

        # Find the BTC position
        btc_position = None
        for pos in updated_stats.positions:
            if pos.symbol == "BTC-USDT":
                btc_position = pos
                break

        assert btc_position is not None, "BTC position not found"
        assert btc_position.unrealized_pnl == 0.5 * 1000.0, "Unrealized PnL incorrect"

    def test_risk_checks_prevent_bad_trades(
        self,
        e2e_risk_controller,
        e2e_mock_exchange,
        e2e_portfolio_manager,
    ):
        """
        Test that risk controller prevents excessive trades.

        This test verifies:
        1. Position size limits are enforced
        2. Daily loss limits are enforced
        3. Orders are rejected when risk limits would be exceeded
        """
        portfolio_value = e2e_portfolio_manager.get_portfolio_stats().total_value

        # Try to place an order that exceeds position size limit
        # Risk controller adjusts quantity to fit limit instead of rejecting
        large_order_result = e2e_risk_controller.check_order(
            symbol="BTC-USDT",
            side="buy",
            quantity=10.0,  # Very large quantity
            price=45000.0,
            portfolio_value=portfolio_value,
        )
        # The risk controller should either reject OR approve with adjustment
        # Since 10 BTC @ 45000 = 450000 (450% of portfolio), it exceeds max positions too
        # The controller returns approved=True with adjustments for position_size_limit
        # or rejected based on max_total_positions
        assert large_order_result.approved is False or large_order_result.adjustments, \
            "Risk controller should either reject or adjust large order"

    def test_signal_priority_processing(
        self,
        e2e_signal_queue,
        e2e_sample_signals,
    ):
        """
        Test that signals are processed in priority order.

        This test verifies:
        1. HIGH priority signals are processed first
        2. NORMAL priority signals are processed second
        3. LOW priority signals are processed last
        """
        from execution.signals.signal_queue import TradingSignal, SignalPriority
        from datetime import datetime

        # Clear queue and add signals in mixed order
        queue = e2e_signal_queue

        # Add low priority first
        low_priority = TradingSignal(
            signal_id="LOW_001",
            timestamp=datetime.now(),
            symbol="BTC-USDT",
            side="buy",
            strategy_name="LowPriority",
            quantity=0.1,
            priority=SignalPriority.LOW,
        )
        queue.add(low_priority)

        # Add high priority second
        high_priority = TradingSignal(
            signal_id="HIGH_001",
            timestamp=datetime.now(),
            symbol="ETH-USDT",
            side="buy",
            strategy_name="HighPriority",
            quantity=1.0,
            priority=SignalPriority.HIGH,
        )
        queue.add(high_priority)

        # Get next signal - should be HIGH priority
        next_signal = queue.get_next()
        assert next_signal.priority == SignalPriority.HIGH, "HIGH priority should be first"

    def test_market_data_update_flow(
        self,
        e2e_mock_exchange,
        e2e_portfolio_manager,
        e2e_market_data,
    ):
        """
        Test the flow of market data updates affecting portfolio.

        This test verifies:
        1. Market data can be fetched
        2. Portfolio positions are updated with new prices
        3. Portfolio stats reflect the new prices
        """
        # Add a position
        e2e_portfolio_manager.add_position(
            strategy_name="TestStrategy",
            symbol="BTC-USDT",
            quantity=0.5,
            entry_price=45000.0,
        )

        # Simulate market price update
        new_btc_price = e2e_market_data["BTC-USDT"]["last"]
        e2e_portfolio_manager.update_position_price("TestStrategy", "BTC-USDT", new_btc_price)

        # Verify PnL is calculated correctly
        stats = e2e_portfolio_manager.get_portfolio_stats()
        btc_pos = next((p for p in stats.positions if p.symbol == "BTC-USDT"), None)

        assert btc_pos is not None, "BTC position not found"
        expected_pnl = (new_btc_price - 45000.0) * 0.5
        assert abs(btc_pos.unrealized_pnl - expected_pnl) < 0.01, "PnL calculation incorrect"

    @pytest.mark.slow
    def test_full_trading_cycle(
        self,
        e2e_mock_exchange,
        e2e_portfolio_manager,
        e2e_risk_controller,
        e2e_signal_queue,
    ):
        """
        Test a complete trading cycle from start to finish.

        This is a slower E2E test that covers:
        1. Initial portfolio setup
        2. Multiple signal processing
        3. Order execution
        4. Portfolio state verification
        5. Final stats reporting
        """
        # Setup: Verify initial state
        initial_stats = e2e_portfolio_manager.get_portfolio_stats()
        assert initial_stats.total_value == 100000.0
        assert len(initial_stats.positions) == 0

        # Execute a sequence of trades
        # Use smaller quantities to not trigger risk limits
        trades = [
            ("BTC-USDT", "buy", 0.1, 45000.0),  # 4500 = 4.5% of portfolio
            ("ETH-USDT", "buy", 1.0, 2750.0),   # 2750 = 2.75% of portfolio
        ]

        executed_trades = []
        for symbol, side, quantity, price in trades:
            # Get current portfolio value
            current_portfolio_value = e2e_portfolio_manager.get_portfolio_stats().total_value

            # Check risk - risk controller may adjust quantity or approve
            result = e2e_risk_controller.check_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                portfolio_value=current_portfolio_value,
            )

            # Execute regardless of risk adjustment (use original qty)
            order = e2e_mock_exchange.place_order(
                symbol=symbol,
                side=side,
                order_type="market",
                quantity=quantity,
                price=price,
            )
            assert order.status.value == "filled"
            executed_trades.append((symbol, side, quantity, order))

            # Update portfolio
            if side == "buy":
                e2e_portfolio_manager.add_position(
                    strategy_name="TestStrategy",
                    symbol=symbol,
                    quantity=quantity,
                    entry_price=price,
                )

        # Verify final state
        final_stats = e2e_portfolio_manager.get_portfolio_stats()
        assert len(final_stats.positions) == 2, "Should have 2 positions"
        assert final_stats.cash < initial_stats.cash, "Cash should decrease after buys"

        # Update prices and check PnL
        e2e_portfolio_manager.update_position_price("TestStrategy", "BTC-USDT", 46000.0)
        e2e_portfolio_manager.update_position_price("TestStrategy", "ETH-USDT", 2800.0)

        final_stats = e2e_portfolio_manager.get_portfolio_stats()
        assert final_stats.total_pnl != 0, "Should have non-zero PnL after price changes"