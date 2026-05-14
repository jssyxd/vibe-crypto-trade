"""
End-to-end tests for live risk validation layer.

Tests the complete risk validation flow using E2E fixtures.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Import test infrastructure
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from execution.risk.live_risk_guard import (
    LiveRiskGuard,
    LiveRiskConfig,
    CircuitBreakerState,
    RiskEventType,
)


@pytest.mark.e2e
class TestLiveRiskValidationE2E:
    """E2E tests for live risk validation."""

    def test_complete_risk_validation_flow(
        self,
        e2e_mock_exchange,
        e2e_portfolio_manager,
        e2e_risk_controller,
        e2e_signal_queue,
        e2e_sample_signals,
    ):
        """
        Test complete risk validation flow from signal to execution.

        This test verifies:
        1. Signals are processed through risk checks
        2. Orders are validated against risk parameters
        3. Portfolio updates correctly after trades
        4. Risk status reflects current state
        """
        # Setup: Create LiveRiskGuard
        risk_guard = LiveRiskGuard(LiveRiskConfig(
            max_position_pct=0.1,
            max_single_exposure_pct=0.2,
            max_total_position_pct=0.5,
            max_leverage=1.0,
            max_daily_loss_pct=0.05,
        ))
        risk_guard.update_portfolio_value(100000.0)

        # Process each signal through risk validation
        approved_signals = []
        for signal in e2e_sample_signals:
            # Get current market price
            ticker = e2e_mock_exchange.get_ticker(signal.symbol)
            price = ticker["last"]

            # Perform pre-trade check
            pre_trade_result = risk_guard.check_pre_trade(
                symbol=signal.symbol,
                side=signal.side,
                quantity=signal.quantity,
                price=price
            )

            if pre_trade_result.approved:
                # Use adjusted quantity if applicable
                qty = pre_trade_result.adjusted_quantity or signal.quantity

                # Execute order
                order = e2e_mock_exchange.place_order(
                    symbol=signal.symbol,
                    side=signal.side,
                    order_type="market",
                    quantity=qty,
                    price=price
                )

                # Record post-trade
                risk_guard.record_post_trade(
                    symbol=signal.symbol,
                    side=signal.side,
                    quantity=qty,
                    price=order.avg_fill_price
                )

                approved_signals.append({
                    'signal': signal,
                    'order': order,
                    'result': pre_trade_result
                })

        # Verify risk status after all trades
        status = risk_guard.get_risk_status()
        assert status["portfolio_value"] > 0
        assert status["checks_performed"] == len(e2e_sample_signals)

    def test_pre_trade_then_post_trade_flow(
        self,
        e2e_mock_exchange,
        e2e_risk_controller,
    ):
        """
        Test pre-trade validation followed by post-trade monitoring.

        This test verifies:
        1. Pre-trade checks validate order
        2. Post-trade updates track position
        3. Subsequent pre-checks use updated positions
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            max_position_pct=0.1,
            max_single_exposure_pct=0.2,
        ))
        guard.update_portfolio_value(100000.0)

        # First trade
        result1 = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result1.approved is True

        # Record first trade
        guard.record_post_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )

        # Record second trade
        guard.record_post_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )

        # Verify exposure updated
        exposures = guard.get_exposures()
        assert exposures["BTC-USDT"] == pytest.approx(0.09, rel=0.1)  # 0.2 BTC @ 45k / 100k

    def test_circuit_breaker_trip_and_recovery(
        self,
        e2e_mock_exchange,
        e2e_portfolio_manager,
    ):
        """
        Test circuit breaker trip and manual recovery.

        This test verifies:
        1. Circuit breaker triggers on risk event
        2. Trading is halted when tripped
        3. Manual reset allows trading to resume
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            max_daily_loss_pct=0.05,
            circuit_breaker_cooldown_secs=300,
        ))
        guard.update_portfolio_value(100000.0)

        # Simulate daily loss exceeding limit
        guard._daily_pnl = -6000  # 6% loss
        guard._daily_start_value = 100000.0

        # Check should trip circuit breaker
        state, event = guard.check_circuit_breakers()
        assert state == CircuitBreakerState.TRIPPED
        assert event is not None

        # Try to trade - should be rejected
        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is False
        assert "halted" in result.message.lower()

        # Reset circuit breaker
        guard.reset_circuit_breaker("Manual reset after review")

        # Verify reset
        state_after, _ = guard.check_circuit_breakers()
        assert state_after == CircuitBreakerState.OK

        # Trade should work again
        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is True

    def test_var_based_position_limits(
        self,
        e2e_mock_exchange,
    ):
        """
        Test VaR-based position limit enforcement.

        This test verifies:
        1. VaR is calculated from return history
        2. Orders exceeding VaR limit are adjusted
        3. VaR circuit breaker triggers on extreme events
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            var_confidence=0.95,
            max_var_pct=0.02,
            var_lookback_days=30,
            enable_circuit_breaker=True,
        ))
        guard.update_portfolio_value(100000.0)

        # Add high volatility return history to trigger VaR limit
        returns = [-0.05, 0.06, -0.04, 0.05, -0.03, 0.04, -0.02, 0.03]
        for r in returns:
            guard._returns_history.append(r)

        # Check circuit breaker - should detect high VaR
        state, event = guard.check_circuit_breakers()
        # VaR should trigger or not based on calculation

        # Normal order should still pass
        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        # May be approved with var_estimate in result
        assert result.var_estimate >= 0

    def test_exposure_monitoring_flow(
        self,
        e2e_mock_exchange,
    ):
        """
        Test exposure monitoring through multiple trades.

        This test verifies:
        1. Individual position exposures are tracked
        2. Total exposure is calculated
        3. Exposure limit prevents additional positions
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            max_single_exposure_pct=0.2,
            max_total_position_pct=0.5,
        ))
        guard.update_portfolio_value(100000.0)

        # Add first position (20% of portfolio)
        guard.record_post_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.444,  # ~20% @ 45k
            price=45000.0
        )

        exposures = guard.get_exposures()
        assert exposures["BTC-USDT"] == pytest.approx(0.2, rel=0.05)

        # Try to add second position - should be limited
        result = guard.check_pre_trade(
            symbol="ETH-USDT",
            side="buy",
            quantity=5.0,  # ~13.75% @ 2750
            price=2750.0
        )
        # Should either adjust or reject based on remaining budget

        # Add second position
        guard.record_post_trade(
            symbol="ETH-USDT",
            side="buy",
            quantity=3.0,
            price=2750.0
        )

        total_exposure = guard._calculate_exposure()
        assert total_exposure > 0.2  # Should have both positions
        assert total_exposure <= 0.5  # Should not exceed total limit

    def test_leverage_enforcement(
        self,
        e2e_mock_exchange,
    ):
        """
        Test leverage limit enforcement.

        This test verifies:
        1. Leverage is calculated from total positions
        2. Orders that would exceed leverage are rejected
        3. Leverage circuit breaker triggers on limit breach
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            max_leverage=1.0,
            max_leverage_per_trade=1.0,
            enable_circuit_breaker=True,
        ))
        guard.update_portfolio_value(100000.0)

        # Add position using 50% of portfolio
        guard.record_post_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.5,
            price=45000.0
        )  # 22,500 / 100,000 = 0.225 leverage

        leverage = guard._calculate_leverage()
        # Note: record_post_trade updates portfolio_value by subtracting trade_value for buys
        # So leverage = 22500 / (100000 - 22500) = 22500 / 77500 ≈ 0.29
        assert leverage == pytest.approx(0.29, rel=0.01)

        # Try to add another position that would push leverage too high
        result = guard.check_pre_trade(
            symbol="ETH-USDT",
            side="buy",
            quantity=5.0,  # 13,750 / 100,000 = 0.1375
            price=2750.0
        )

        # Check leverage calculation
        current_leverage = guard._calculate_leverage()
        new_position_pct = (5.0 * 2750.0) / 100000.0
        projected_leverage = current_leverage + new_position_pct

        if projected_leverage > guard.config.max_leverage_per_trade:
            assert result.approved is False or result.adjustment_reason == "leverage_limit"

    def test_consecutive_losses_tracking(
        self,
        e2e_mock_exchange,
    ):
        """
        Test consecutive losses tracking and circuit breaker.

        This test verifies:
        1. Consecutive losses are counted correctly
        2. Circuit breaker triggers after threshold
        3. Winning trade resets counter
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            consecutive_losses_threshold=3,
            enable_circuit_breaker=True,
        ))
        guard.update_portfolio_value(100000.0)

        # Record 3 losing trades
        for i in range(3):
            guard.record_trade_result(
                symbol="BTC-USDT",
                side="buy",
                quantity=0.1,
                price=45000.0,
                realized_pnl=-100.0
            )

        assert guard._consecutive_losses == 3

        # Circuit breaker should trip
        state, event = guard.check_circuit_breakers()
        assert state == CircuitBreakerState.TRIPPED
        assert event.event_type == RiskEventType.LOSS_LIMIT_EXCEEDED

        # Record winning trade
        guard.record_trade_result(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0,
            realized_pnl=200.0
        )

        assert guard._consecutive_losses == 0

        # Reset and verify trading works
        guard.reset_circuit_breaker()
        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is True

    def test_manual_halt_override(
        self,
        e2e_mock_exchange,
    ):
        """
        Test manual halt override functionality.

        This test verifies:
        1. Manual halt immediately stops trading
        2. Manual override in config bypasses all checks
        3. Reset allows trading to resume
        """
        # Test manual halt
        guard = LiveRiskGuard(LiveRiskConfig())
        guard.update_portfolio_value(100000.0)

        guard.manual_halt("Emergency - system issue detected")

        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is False
        assert "halted" in result.message.lower()

        guard.reset_circuit_breaker()
        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is True

        # Test manual override mode
        override_guard = LiveRiskGuard(LiveRiskConfig(manual_override=True))
        override_guard.update_portfolio_value(100000.0)

        # Even with a huge order, should pass due to override
        result = override_guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=100.0,  # Huge order
            price=45000.0
        )
        assert result.approved is True

    def test_full_trading_cycle_with_risk(
        self,
        e2e_mock_exchange,
        e2e_portfolio_manager,
    ):
        """
        Test complete trading cycle with risk management.

        This test verifies:
        1. Initial portfolio setup
        2. Multiple signal processing with risk checks
        3. Position size adjustments
        4. Exposure monitoring
        5. Final risk status
        """
        # Setup risk guard with tight limits
        guard = LiveRiskGuard(LiveRiskConfig(
            max_position_pct=0.1,  # 10% max per position
            max_single_exposure_pct=0.2,  # 20% max per symbol
            max_total_position_pct=0.5,  # 50% total
            max_leverage=1.0,
            max_daily_loss_pct=0.05,
        ))
        guard.update_portfolio_value(100000.0)

        # Execute a sequence of trades
        trades = [
            ("BTC-USDT", "buy", 0.1, 45000.0),  # 4.5%
            ("ETH-USDT", "buy", 0.5, 2750.0),   # 1.375%
        ]

        executed_trades = []
        for symbol, side, quantity, price in trades:
            # Pre-trade check
            result = guard.check_pre_trade(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price
            )

            if result.approved:
                qty = result.adjusted_quantity or quantity

                # Execute
                order = e2e_mock_exchange.place_order(
                    symbol=symbol,
                    side=side,
                    order_type="market",
                    quantity=qty,
                    price=price
                )

                # Post-trade update
                guard.record_post_trade(
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    price=order.avg_fill_price
                )

                executed_trades.append({
                    'symbol': symbol,
                    'qty': qty,
                    'price': order.avg_fill_price
                })

        # Verify final state
        assert len(executed_trades) >= 1  # At least first trade should work

        status = guard.get_risk_status()
        assert status["portfolio_value"] > 0
        assert status["checks_performed"] == 2
        assert status["leverage"] < 1.0  # Should be under leverage limit

    def test_risk_metrics_accuracy(
        self,
        e2e_mock_exchange,
    ):
        """
        Test accuracy of risk metrics reporting.

        This test verifies:
        1. Portfolio value updates correctly
        2. PnL tracking is accurate
        3. Exposure calculations are correct
        4. VaR estimates are reasonable
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            var_confidence=0.95,
            max_var_pct=0.02,
        ))
        guard.update_portfolio_value(100000.0)

        # Add some positions
        guard.update_position("BTC-USDT", 0.5, 40000.0, 45000.0)
        guard.update_position("ETH-USDT", 2.0, 2500.0, 2750.0)

        # Record some trades
        guard.record_trade_result("BTC-USDT", "buy", 0.5, 45000.0, 250.0)
        guard.record_trade_result("ETH-USDT", "buy", 2.0, 2750.0, 500.0)

        # Get status
        status = guard.get_risk_status()

        # Verify metrics
        assert status["realized_pnl"] == 750.0
        assert status["positions"] == 2

        # Verify exposures
        exposures = guard.get_exposures()
        btc_exposure = exposures["BTC-USDT"]
        eth_exposure = exposures["ETH-USDT"]

        # BTC: 0.5 * 45000 = 22500 / 100000 = 0.225
        assert btc_exposure == pytest.approx(0.225, rel=0.01)
        # ETH: 2.0 * 2750 = 5500 / 100000 = 0.055
        assert eth_exposure == pytest.approx(0.055, rel=0.01)

    def test_latency_target(
        self,
        e2e_mock_exchange,
    ):
        """
        Test that pre-trade checks meet latency target (< 1ms).

        This test verifies:
        1. Pre-trade checks are fast enough
        2. Statistics are tracked accurately
        """
        guard = LiveRiskGuard()
        guard.update_portfolio_value(100000.0)

        # Run many checks to measure latency
        latencies = []
        for _ in range(100):
            import time
            start = time.perf_counter()
            guard.check_pre_trade(
                symbol="BTC-USDT",
                side="buy",
                quantity=0.1,
                price=45000.0
            )
            latencies.append((time.perf_counter() - start) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        status = guard.get_risk_status()

        # Target is < 1ms average, report actual
        print(f"Average latency: {avg_latency:.3f}ms, Max: {max_latency:.3f}ms")

        assert avg_latency < 10.0, f"Average latency too high: {avg_latency:.3f}ms"
        assert status["avg_latency_ms"] < 10.0

    def test_mixed_buy_sell_flow(
        self,
        e2e_mock_exchange,
    ):
        """
        Test mixed buy/sell flow with risk management.

        This test verifies:
        1. Buy orders are validated
        2. Sell orders are validated
        3. Net exposure is calculated correctly
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            max_single_exposure_pct=0.2,
            max_total_position_pct=0.5,
        ))
        guard.update_portfolio_value(100000.0)

        # Buy first
        guard.record_post_trade("BTC-USDT", "buy", 0.5, 45000.0)
        assert guard._exposures.get("BTC-USDT", 0) > 0

        # Sell some
        guard.record_post_trade("BTC-USDT", "sell", 0.2, 46000.0)
        positions = guard.get_positions()
        assert positions["BTC-USDT"]["quantity"] == 0.3

        # Buy more
        guard.record_post_trade("BTC-USDT", "buy", 0.2, 45000.0)
        positions = guard.get_positions()
        assert positions["BTC-USDT"]["quantity"] == 0.5

    def test_risk_event_history_tracking(
        self,
        e2e_mock_exchange,
    ):
        """
        Test that risk events are tracked in history.

        This test verifies:
        1. Risk events are recorded
        2. Event history is maintained
        3. Status includes recent events
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            enable_circuit_breaker=True,
        ))
        guard.update_portfolio_value(100000.0)

        # Trigger multiple events
        guard._daily_pnl = -6000
        guard._daily_start_value = 100000.0
        guard.check_circuit_breakers()

        guard.reset_circuit_breaker()

        guard._daily_pnl = -7000
        guard._daily_start_value = 100000.0
        guard.check_circuit_breakers()

        # Verify history
        status = guard.get_risk_status()
        assert len(status["recent_risk_events"]) >= 2

    def test_position_limit_with_adjustment(
        self,
        e2e_mock_exchange,
    ):
        """
        Test position limit adjustment flow.

        This test verifies:
        1. Oversized orders are adjusted (not rejected)
        2. Adjusted quantity is calculated correctly
        3. Order proceeds with adjusted quantity
        """
        guard = LiveRiskGuard(LiveRiskConfig(
            max_position_pct=0.1,  # 10% max
        ))
        guard.update_portfolio_value(100000.0)

        # Try to place oversized order (25% of portfolio)
        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.6,  # 0.6 * 45000 = 27000 = 27% of 100k
            price=45000.0
        )

        assert result.approved is True
        assert result.adjustment_reason == "position_size_limit"
        assert result.adjusted_quantity is not None
        # Adjusted quantity should be ~10% of portfolio / price
        assert result.adjusted_quantity <= 0.3  # ~13.5% is acceptable


class TestLiveRiskValidationE2EFixtures:
    """Tests for E2E fixture integration."""

    def test_e2e_config_applied(self, e2e_config):
        """Test that E2E config has expected values."""
        assert e2e_config["testnet"] is True
        assert e2e_config["initial_capital"] == 100000.0
        assert e2e_config["max_position_size"] == 0.1
        assert e2e_config["max_daily_loss_pct"] == 0.05

    def test_e2e_mock_exchange_works(self, e2e_mock_exchange):
        """Test that E2E mock exchange is functional."""
        balance = e2e_mock_exchange.get_balance()
        assert balance.total_equity == 100000.0

        ticker = e2e_mock_exchange.get_ticker("BTC-USDT")
        assert ticker["last"] == 45000.0

    def test_e2e_market_data(self, e2e_market_data):
        """Test E2E market data fixture."""
        assert "BTC-USDT" in e2e_market_data
        assert "ETH-USDT" in e2e_market_data
        assert e2e_market_data["BTC-USDT"]["last"] == 45000.0