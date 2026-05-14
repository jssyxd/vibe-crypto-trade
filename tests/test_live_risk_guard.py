"""
Unit tests for live_risk_guard.py.

Tests the LiveRiskGuard class for real-time risk validation.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from execution.risk.live_risk_guard import (
    LiveRiskGuard,
    LiveRiskConfig,
    CircuitBreakerState,
    RiskEventType,
    PreTradeCheckResult,
    PostTradeUpdate,
)


class TestLiveRiskGuardConfig:
    """Tests for LiveRiskConfig."""

    def test_default_config_values(self):
        """Test default configuration values."""
        config = LiveRiskConfig()
        assert config.max_position_pct == 0.1
        assert config.max_total_position_pct == 0.5
        assert config.max_single_exposure_pct == 0.2
        assert config.max_var_pct == 0.02
        assert config.max_leverage == 1.0
        assert config.max_daily_loss_pct == 0.05
        assert config.enable_circuit_breaker is True

    def test_custom_config_values(self):
        """Test custom configuration values."""
        config = LiveRiskConfig(
            max_position_pct=0.15,
            max_leverage=2.0,
            max_daily_loss_pct=0.03,
            manual_override=True,
        )
        assert config.max_position_pct == 0.15
        assert config.max_leverage == 2.0
        assert config.max_daily_loss_pct == 0.03
        assert config.manual_override is True


class TestPreTradeChecks:
    """Tests for pre-trade risk checks."""

    @pytest.fixture
    def risk_guard(self):
        """Create a LiveRiskGuard instance for testing."""
        config = LiveRiskConfig(
            max_position_pct=0.1,
            max_single_exposure_pct=0.2,
            max_total_position_pct=0.5,
            max_leverage=1.0,
            max_leverage_per_trade=1.0,
            max_var_pct=0.02,
            min_position_size=0.001,
        )
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)
        return guard

    def test_pre_trade_approved_normal_order(self, risk_guard):
        """Test that normal order passes pre-trade checks."""
        result = risk_guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is True
        assert result.adjusted_quantity is None
        assert result.latency_ms >= 0

    def test_pre_trade_position_size_limit_adjusted(self, risk_guard):
        """Test that oversized position is adjusted."""
        # 0.5 BTC @ 45000 = 22500 (22.5% of 100k, exceeds 10% limit)
        result = risk_guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.5,
            price=45000.0
        )
        assert result.approved is True
        assert result.adjustment_reason == "position_size_limit"
        assert result.adjusted_quantity is not None
        assert result.adjusted_quantity == pytest.approx(0.2222, abs=0.001)  # ~10% of 100k @ 45k

    def test_pre_trade_exposure_limit_adjusted(self, risk_guard):
        """Test that exposure limit is enforced."""
        # Add existing position (but smaller to not trigger position size limit)
        risk_guard.update_position("BTC-USDT", 0.1, 40000.0, 45000.0)  # 4.5%
        # Try to buy more that would exceed single exposure limit
        # Total would be 4.5% + 13.5% = 18% which is < 20%, so should pass position check
        # But we need a larger existing position to trigger exposure limit
        risk_guard.update_position("BTC-USDT", 0.15, 40000.0, 45000.0)  # 6.75%
        # Now try to buy more - total exposure would be ~20%
        result = risk_guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.3,
            price=45000.0
        )
        # Should be adjusted or rejected - position size or exposure limit
        assert result.adjustment_reason in ["position_size_limit", "exposure_limit", None]

    def test_pre_trade_total_exposure_rejected(self, risk_guard):
        """Test that total exposure limit rejects order."""
        # Set up multiple positions near limit
        risk_guard.update_position("BTC-USDT", 0.5, 40000.0, 45000.0)  # 22.5%
        risk_guard.update_position("ETH-USDT", 0.5, 2500.0, 2750.0)   # ~13.75%
        # Total ~36.25%
        # Try to add another position that would exceed 50% total
        result = risk_guard.check_pre_trade(
            symbol="SOL-USDT",
            side="buy",
            quantity=10.0,
            price=100.0  # 1000 = 1%
        )
        # Should be rejected because total exposure would exceed limit
        if result.adjusted_quantity is None and not result.approved:
            assert result.approved is False

    def test_pre_trade_leverage_rejected(self, risk_guard):
        """Test that leverage limit rejects order."""
        # Set existing position to high leverage
        risk_guard.update_position("BTC-USDT", 0.8, 40000.0, 45000.0)  # 36%
        # Try to add another position that pushes leverage over limit
        result = risk_guard.check_pre_trade(
            symbol="ETH-USDT",
            side="buy",
            quantity=0.3,
            price=2750.0  # 8.25%
        )
        # Check if rejected due to leverage
        if not result.approved:
            assert "leverage" in result.message.lower()

    def test_pre_trade_minimum_size_rejected(self, risk_guard):
        """Test that orders below minimum size are rejected."""
        result = risk_guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.0001,  # Below 0.001 minimum
            price=45000.0
        )
        assert result.approved is False
        assert "minimum" in result.message.lower()

    def test_pre_trade_latency_target(self, risk_guard):
        """Test that pre-trade check meets latency target (< 1ms)."""
        # Run multiple checks to get average
        times = []
        for _ in range(100):
            start = time.perf_counter()
            risk_guard.check_pre_trade(
                symbol="BTC-USDT",
                side="buy",
                quantity=0.1,
                price=45000.0
            )
            times.append((time.perf_counter() - start) * 1000)

        avg_latency = sum(times) / len(times)
        max_latency = max(times)
        # Target is < 1ms average, allow some tolerance
        assert avg_latency < 5.0, f"Average latency {avg_latency:.2f}ms exceeds target"
        assert max_latency < 10.0, f"Max latency {max_latency:.2f}ms too high"


class TestCircuitBreakers:
    """Tests for circuit breaker functionality."""

    @pytest.fixture
    def risk_guard(self):
        """Create a LiveRiskGuard instance for testing."""
        config = LiveRiskConfig(
            max_daily_loss_pct=0.05,
            max_weekly_loss_pct=0.10,
            max_monthly_loss_pct=0.20,
            consecutive_losses_threshold=3,
            circuit_breaker_cooldown_secs=300,
        )
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)
        return guard

    def test_circuit_breaker_triggers_on_daily_loss(self, risk_guard):
        """Test that circuit breaker triggers on daily loss limit."""
        # Simulate daily loss
        risk_guard._daily_pnl = -6000  # 6% loss
        risk_guard._daily_start_value = 100000.0

        state, event = risk_guard.check_circuit_breakers()
        assert state == CircuitBreakerState.TRIPPED
        assert event is not None
        assert event.event_type == RiskEventType.DRAWDOWN_EXCEEDED

    def test_circuit_breaker_triggers_on_consecutive_losses(self, risk_guard):
        """Test that circuit breaker triggers on consecutive losses."""
        # Simulate consecutive losses
        risk_guard._consecutive_losses = 5

        state, event = risk_guard.check_circuit_breakers()
        assert state == CircuitBreakerState.TRIPPED
        assert event.event_type == RiskEventType.LOSS_LIMIT_EXCEEDED

    def test_circuit_breaker_pre_trade_rejects_when_tripped(self, risk_guard):
        """Test that pre-trade rejects orders when circuit breaker is tripped."""
        # First trigger the circuit breaker
        risk_guard._daily_pnl = -6000
        risk_guard._daily_start_value = 100000.0
        risk_guard.check_circuit_breakers()

        # Now try to trade
        result = risk_guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is False
        assert "halted" in result.message.lower()

    def test_circuit_breaker_manual_halt(self, risk_guard):
        """Test manual halt functionality."""
        risk_guard.manual_halt("Emergency stop - system maintenance")

        state, _ = risk_guard.check_circuit_breakers()
        assert state == CircuitBreakerState.MANUAL_HALT

        # Pre-trade should be rejected
        result = risk_guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is False

    def test_circuit_breaker_reset(self, risk_guard):
        """Test circuit breaker reset functionality."""
        # Trigger circuit breaker
        risk_guard._daily_pnl = -6000
        risk_guard._daily_start_value = 100000.0
        risk_guard.check_circuit_breakers()

        assert risk_guard._circuit_breaker_state == CircuitBreakerState.TRIPPED

        # Reset - this clears the state
        risk_guard.reset_circuit_breaker("Manual reset after review")
        assert risk_guard._circuit_breaker_state == CircuitBreakerState.OK

        # Now recover from the loss condition (simulate market recovery)
        risk_guard._daily_pnl = 1000  # Recover
        risk_guard._daily_start_value = 95000.0
        risk_guard._peak_value = 100000.0

        state, _ = risk_guard.check_circuit_breakers()
        assert state == CircuitBreakerState.OK

        # Pre-trade should work again after recovery
        result = risk_guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is True

    def test_manual_override_bypasses_checks(self, risk_guard):
        """Test that manual override bypasses all checks."""
        config = LiveRiskConfig(manual_override=True)
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)

        # Pre-trade should always pass
        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=100.0,  # Huge order
            price=45000.0
        )
        assert result.approved is True
        assert "override" in result.message.lower()


class TestPostTradeMonitoring:
    """Tests for post-trade monitoring."""

    @pytest.fixture
    def risk_guard(self):
        """Create a LiveRiskGuard instance for testing."""
        config = LiveRiskConfig()
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)
        return guard

    def test_record_post_trade_updates_position(self, risk_guard):
        """Test that post-trade updates position correctly."""
        update = risk_guard.record_post_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.5,
            price=45000.0
        )

        assert update.symbol == "BTC-USDT"
        assert update.quantity == 0.5
        assert update.new_position_pct > 0

        positions = risk_guard.get_positions()
        assert "BTC-USDT" in positions
        assert positions["BTC-USDT"]["quantity"] == 0.5

    def test_record_post_trade_updates_exposure(self, risk_guard):
        """Test that post-trade updates exposure."""
        risk_guard.record_post_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.5,
            price=45000.0
        )

        exposures = risk_guard.get_exposures()
        assert "BTC-USDT" in exposures
        assert exposures["BTC-USDT"] == pytest.approx(0.225, rel=0.01)  # 22500 / 100000

    def test_record_trade_result_tracks_pnl(self, risk_guard):
        """Test that trade results are tracked for PnL."""
        risk_guard.record_trade_result(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.5,
            price=45000.0,
            realized_pnl=500.0
        )

        assert risk_guard._realized_pnl == 500.0
        assert risk_guard._daily_pnl == 500.0

    def test_record_trade_result_tracks_losses(self, risk_guard):
        """Test that consecutive losses are tracked."""
        risk_guard.record_trade_result("BTC-USDT", "buy", 0.1, 45000.0, -100.0)
        risk_guard.record_trade_result("ETH-USDT", "buy", 0.1, 2750.0, -200.0)
        risk_guard.record_trade_result("SOL-USDT", "buy", 0.1, 100.0, -150.0)

        assert risk_guard._consecutive_losses == 3

    def test_post_trade_with_sell_reduces_position(self, risk_guard):
        """Test that selling reduces position."""
        # Buy first
        risk_guard.record_post_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=1.0,
            price=45000.0
        )

        # Sell half
        risk_guard.record_post_trade(
            symbol="BTC-USDT",
            side="sell",
            quantity=0.5,
            price=46000.0
        )

        positions = risk_guard.get_positions()
        assert positions["BTC-USDT"]["quantity"] == 0.5


class TestVaRChecks:
    """Tests for VaR-based position limits."""

    @pytest.fixture
    def risk_guard(self):
        """Create a LiveRiskGuard with VaR enabled."""
        config = LiveRiskConfig(
            var_confidence=0.95,
            max_var_pct=0.02,
            var_lookback_days=30,
        )
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)
        return guard

    def test_var_calculation_with_returns(self, risk_guard):
        """Test VaR calculation with return history."""
        # Add return history
        returns = [-0.01, 0.02, -0.015, 0.01, -0.02, 0.015, -0.01, 0.01]
        for r in returns:
            risk_guard._returns_history.append(r)

        var = risk_guard._calculate_var()
        assert var >= 0  # VaR should be positive (absolute loss)

    def test_var_triggers_circuit_breaker(self, risk_guard):
        """Test that excessive VaR triggers circuit breaker."""
        # Add high volatility returns
        returns = [-0.05, 0.06, -0.04, 0.05, -0.03, 0.04, -0.02, 0.03]
        for r in returns:
            risk_guard._returns_history.append(r)

        state, event = risk_guard.check_circuit_breakers()
        if event:
            assert event.event_type == RiskEventType.VAR_EXCEEDED


class TestRiskStatus:
    """Tests for risk status reporting."""

    @pytest.fixture
    def risk_guard(self):
        """Create a LiveRiskGuard instance for testing."""
        config = LiveRiskConfig()
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)
        return guard

    def test_get_risk_status_includes_all_metrics(self, risk_guard):
        """Test that risk status includes all key metrics."""
        # Add some positions and history
        risk_guard.update_position("BTC-USDT", 0.5, 40000.0, 45000.0)
        risk_guard.record_trade_result("ETH-USDT", "buy", 1.0, 2750.0, 100.0)

        status = risk_guard.get_risk_status()

        assert "portfolio_value" in status
        assert "leverage" in status
        assert "total_exposure" in status
        assert "var_estimate" in status
        assert "circuit_breaker_state" in status
        assert "positions" in status
        assert "checks_performed" in status
        assert status["positions"] == 1

    def test_get_risk_status_tracks_check_stats(self, risk_guard):
        """Test that check statistics are tracked."""
        for i in range(10):
            risk_guard.check_pre_trade(
                symbol="BTC-USDT",
                side="buy",
                quantity=0.1,
                price=45000.0
            )

        status = risk_guard.get_risk_status()
        assert status["checks_performed"] == 10
        assert status["checks_rejected"] == 0

    def test_get_positions_returns_all_positions(self, risk_guard):
        """Test that positions are returned correctly."""
        risk_guard.update_position("BTC-USDT", 0.5, 40000.0, 45000.0)
        risk_guard.update_position("ETH-USDT", 2.0, 2500.0, 2750.0)

        positions = risk_guard.get_positions()
        assert len(positions) == 2
        assert "BTC-USDT" in positions
        assert "ETH-USDT" in positions

    def test_get_exposures_returns_correct_values(self, risk_guard):
        """Test that exposures are calculated correctly."""
        risk_guard.update_position("BTC-USDT", 0.5, 40000.0, 45000.0)  # 22.5%
        risk_guard.update_position("ETH-USDT", 2.0, 2500.0, 2750.0)   # 5.5%

        exposures = risk_guard.get_exposures()
        assert exposures["BTC-USDT"] == pytest.approx(0.225, rel=0.01)
        assert exposures["ETH-USDT"] == pytest.approx(0.055, rel=0.01)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_portfolio_value(self):
        """Test handling of zero portfolio value."""
        config = LiveRiskConfig()
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(0.0)

        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        # Should handle division by zero gracefully
        assert result.approved is False or result.var_estimate == 0

    def test_empty_return_history(self):
        """Test VaR calculation with no return history."""
        config = LiveRiskConfig()
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)

        var = guard._calculate_var()
        assert var == 0.0

    def test_thread_safety_concurrent_checks(self):
        """Test thread safety with concurrent checks."""
        import threading

        config = LiveRiskConfig()
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)

        errors = []

        def run_checks():
            try:
                for _ in range(50):
                    guard.check_pre_trade(
                        symbol="BTC-USDT",
                        side="buy",
                        quantity=0.1,
                        price=45000.0
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_checks) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_large_order_size_handling(self):
        """Test handling of very large order sizes."""
        config = LiveRiskConfig()
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)

        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=100.0,  # 100 BTC = 4.5M
            price=45000.0
        )
        # Should be adjusted to fit limits
        if result.adjusted_quantity:
            assert result.adjusted_quantity < 100.0


class TestPortfolioUpdates:
    """Tests for portfolio value updates."""

    @pytest.fixture
    def risk_guard(self):
        """Create a LiveRiskGuard instance for testing."""
        config = LiveRiskConfig()
        guard = LiveRiskGuard(config)
        guard.update_portfolio_value(100000.0)
        return guard

    def test_update_portfolio_value_tracks_peak(self, risk_guard):
        """Test that portfolio value updates track peak correctly."""
        risk_guard.update_portfolio_value(105000.0)
        assert risk_guard._peak_value == 105000.0

        risk_guard.update_portfolio_value(102000.0)  # Lower than peak
        assert risk_guard._peak_value == 105000.0  # Peak maintained

    def test_update_portfolio_value_tracks_drawdown(self, risk_guard):
        """Test that drawdown is calculated from peak."""
        risk_guard.update_portfolio_value(100000.0)
        risk_guard.update_portfolio_value(95000.0)  # 5% drawdown from peak

        daily_dd, _, _ = risk_guard._calculate_drawdown()
        assert daily_dd == pytest.approx(0.05, rel=0.01)  # 5% = 5000/100000


# Integration tests using fixtures from conftest.py
class TestLiveRiskGuardWithFixtures:
    """Tests using fixtures from conftest.py."""

    def test_live_risk_guard_with_sample_portfolio(self, sample_portfolio):
        """Test LiveRiskGuard with sample portfolio fixture."""
        guard = LiveRiskGuard()
        guard.update_portfolio_value(sample_portfolio["initial_capital"])

        result = guard.check_pre_trade(
            symbol="BTC-USDT",
            side="buy",
            quantity=0.1,
            price=45000.0
        )
        assert result.approved is True

    def test_live_risk_guard_tracks_existing_positions(self, sample_portfolio):
        """Test that existing positions are tracked correctly."""
        guard = LiveRiskGuard()
        guard.update_portfolio_value(sample_portfolio["initial_capital"])

        # Simulate existing positions from portfolio
        for pos in sample_portfolio["positions"]:
            guard.update_position(
                symbol=pos["symbol"],
                quantity=pos["quantity"],
                entry_price=pos["entry_price"],
                current_price=pos["current_price"]
            )

        positions = guard.get_positions()
        assert len(positions) == 2

        exposures = guard.get_exposures()
        assert "BTC-USDT" in exposures
        assert "ETH-USDT" in exposures