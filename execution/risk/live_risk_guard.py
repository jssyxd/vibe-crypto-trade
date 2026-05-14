"""
Live Risk Guard for real-time risk validation layer.

This module provides real-time risk validation including:
- Pre-trade checks (position limits, VaR, exposure)
- Post-trade monitoring
- Automatic circuit breakers
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import time
import threading


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    OK = "ok"
    WARNING = "warning"
    TRIPPED = "tripped"
    MANUAL_HALT = "manual_halt"


class RiskEventType(Enum):
    """Types of risk events that can trigger circuit breakers."""
    DRAWDOWN_EXCEEDED = "drawdown_exceeded"
    VAR_EXCEEDED = "var_exceeded"
    EXPOSURE_EXCEEDED = "exposure_exceeded"
    LEVERAGE_EXCEEDED = "leverage_exceeded"
    POSITION_LIMIT_EXCEEDED = "position_limit_exceeded"
    LOSS_LIMIT_EXCEEDED = "loss_limit_exceeded"
    MANUAL_HALT = "manual_halt"


@dataclass
class RiskEvent:
    """Represents a risk event that occurred."""
    event_type: RiskEventType
    timestamp: datetime
    message: str
    value: float
    threshold: float
    action_taken: str = ""


@dataclass
class PreTradeCheckResult:
    """Result of pre-trade risk check."""
    approved: bool
    message: str
    adjusted_quantity: Optional[float] = None
    adjustment_reason: Optional[str] = None
    var_estimate: float = 0.0
    leverage_used: float = 0.0
    exposure_pct: float = 0.0
    latency_ms: float = 0.0


@dataclass
class PostTradeUpdate:
    """Update after a trade is executed."""
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    portfolio_value_after: float
    new_position_pct: float
    new_exposure_pct: float
    new_leverage: float


@dataclass
class LiveRiskConfig:
    """Configuration for live risk guard."""
    # Position limits
    max_position_pct: float = 0.1  # Max 10% of portfolio per position
    max_total_position_pct: float = 0.5  # Max 50% total exposure
    min_position_size: float = 0.001  # Min order size

    # Exposure limits
    max_single_exposure_pct: float = 0.2  # Max 20% in single symbol
    max_correlated_exposure_pct: float = 0.3  # Max 30% in correlated assets

    # VaR limits
    var_confidence: float = 0.95  # 95% VaR
    max_var_pct: float = 0.02  # Max 2% VaR as % of portfolio
    var_lookback_days: int = 30  # Days of history for VaR

    # Leverage
    max_leverage: float = 1.0  # No leverage by default
    max_leverage_per_trade: float = 1.0

    # Circuit breaker thresholds
    max_daily_loss_pct: float = 0.05  # 5% daily loss
    max_weekly_loss_pct: float = 0.10  # 10% weekly loss
    max_monthly_loss_pct: float = 0.20  # 20% monthly loss
    consecutive_losses_threshold: int = 3  # 3 consecutive losses

    # Monitoring
    enable_circuit_breaker: bool = True
    circuit_breaker_cooldown_secs: int = 300  # 5 min cooldown after trip
    manual_override: bool = False  # Override all checks


class LiveRiskGuard:
    """
    Live Risk Guard for real-time risk validation.

    Features:
    - Pre-trade checks with < 1ms latency target
    - Post-trade monitoring
    - Automatic and manual circuit breakers
    - VaR-based position limits
    - Configurable risk parameters
    """

    def __init__(self, config: Optional[LiveRiskConfig] = None):
        """
        Initialize Live Risk Guard.

        Args:
            config: Risk configuration (uses defaults if not provided)
        """
        self.config = config or LiveRiskConfig()
        self._reset_state()

    def _reset_state(self):
        """Reset internal state."""
        # Portfolio tracking
        self._portfolio_value = 100000.0
        self._peak_value = 100000.0
        self._daily_start_value = 100000.0
        self._weekly_start_value = 100000.0
        self._monthly_start_value = 100000.0
        self._last_reset_date = datetime.now().date()

        # Position tracking
        self._positions: Dict[str, Dict] = {}  # symbol -> position data
        self._position_history: List[Dict] = []
        self._exposures: Dict[str, float] = {}  # symbol -> exposure pct

        # PnL tracking
        self._daily_pnl = 0.0
        self._weekly_pnl = 0.0
        self._monthly_pnl = 0.0
        self._realized_pnl = 0.0
        self._unrealized_pnl = 0.0

        # VaR tracking
        self._returns_history: List[float] = []
        self._var_cache: Optional[float] = None
        self._var_cache_time: Optional[datetime] = None

        # Circuit breaker state
        self._circuit_breaker_state = CircuitBreakerState.OK
        self._circuit_breaker_triggered_at: Optional[datetime] = None
        self._last_risk_event: Optional[RiskEvent] = None
        self._risk_event_history: List[RiskEvent] = []

        # Consecutive losses tracking
        self._consecutive_losses = 0
        self._loss_streak_start: Optional[datetime] = None

        # Manual halt
        self._manual_halt_reason: Optional[str] = None

        # Thread safety
        self._lock = threading.RLock()  # Use RLock for reentrant locking

        # Statistics
        self._checks_performed = 0
        self._checks_rejected = 0
        self._total_latency_ms = 0.0

    def update_portfolio_value(self, portfolio_value: float):
        """Update current portfolio value."""
        with self._lock:
            old_value = self._portfolio_value
            self._portfolio_value = portfolio_value

            # Update peak
            if portfolio_value > self._peak_value:
                self._peak_value = portfolio_value

            # Update PnL
            self._unrealized_pnl = portfolio_value - old_value

            # Check period reset
            self._check_period_reset()

    def _check_period_reset(self):
        """Check if period start values need reset."""
        now = datetime.now().date()

        if now > self._last_reset_date:
            # Reset daily
            self._daily_start_value = self._portfolio_value
            self._daily_pnl = 0.0
            self._consecutive_losses = 0
            self._loss_streak_start = None

            # Reset weekly on Monday
            if now.weekday() == 0:
                self._weekly_start_value = self._portfolio_value
                self._weekly_pnl = 0.0

            # Reset monthly on 1st
            if now.day == 1:
                self._monthly_start_value = self._portfolio_value
                self._monthly_pnl = 0.0

            self._last_reset_date = now

    def update_position(self, symbol: str, quantity: float, entry_price: float,
                        current_price: float):
        """Update position for a symbol."""
        with self._lock:
            if quantity <= 0:
                # Close or remove position
                if symbol in self._positions:
                    del self._positions[symbol]
                if symbol in self._exposures:
                    del self._exposures[symbol]
            else:
                position_value = quantity * current_price
                exposure_pct = position_value / self._portfolio_value

                self._positions[symbol] = {
                    'quantity': quantity,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'value': position_value,
                    'unrealized_pnl': (current_price - entry_price) * quantity,
                }
                self._exposures[symbol] = exposure_pct

    def record_trade_result(self, symbol: str, side: str, quantity: float,
                            price: float, realized_pnl: float = 0.0):
        """Record trade result for monitoring."""
        with self._lock:
            # Update PnL
            self._daily_pnl += realized_pnl
            self._weekly_pnl += realized_pnl
            self._monthly_pnl += realized_pnl
            self._realized_pnl += realized_pnl

            # Track consecutive losses
            if realized_pnl < 0:
                self._consecutive_losses += 1
                if self._loss_streak_start is None:
                    self._loss_streak_start = datetime.now()
            else:
                self._consecutive_losses = 0
                self._loss_streak_start = None

            # Record return for VaR
            if self._portfolio_value > 0:
                return_pct = realized_pnl / self._portfolio_value
                self._returns_history.append(return_pct)
                # Keep history limited
                if len(self._returns_history) > self.config.var_lookback_days:
                    self._returns_history.pop(0)

            # Invalidate VaR cache
            self._var_cache = None

    def _calculate_var(self) -> float:
        """Calculate Value at Risk (historical method)."""
        if len(self._returns_history) < 2:
            return 0.0

        # Check cache (valid for 1 minute)
        if self._var_cache is not None and self._var_cache_time is not None:
            if (datetime.now() - self._var_cache_time).total_seconds() < 60:
                return self._var_cache

        sorted_returns = sorted(self._returns_history)
        n = len(sorted_returns)

        # Calculate VaR at configured confidence
        var_idx = int(n * (1 - self.config.var_confidence))
        var_value = abs(sorted_returns[var_idx]) * self._portfolio_value

        self._var_cache = var_value
        self._var_cache_time = datetime.now()

        return var_value

    def _calculate_exposure(self, symbol: str = None) -> float:
        """Calculate current exposure percentage."""
        if symbol:
            return self._exposures.get(symbol, 0.0)

        total_exposure = sum(self._exposures.values())
        return total_exposure

    def _calculate_leverage(self) -> float:
        """Calculate current leverage (total position value / portfolio value)."""
        total_position_value = sum(
            pos.get('value', 0) for pos in self._positions.values()
        )
        leverage = total_position_value / self._portfolio_value if self._portfolio_value > 0 else 0.0
        return leverage

    def _calculate_drawdown(self) -> Tuple[float, float, float]:
        """Calculate drawdown percentages (daily, weekly, monthly)."""
        daily_dd = (self._peak_value - self._portfolio_value) / self._peak_value if self._peak_value > 0 else 0.0
        weekly_dd = (self._weekly_start_value - self._portfolio_value) / self._weekly_start_value if self._weekly_start_value > 0 else 0.0
        monthly_dd = (self._monthly_start_value - self._portfolio_value) / self._monthly_start_value if self._monthly_start_value > 0 else 0.0
        return daily_dd, weekly_dd, monthly_dd

    def check_pre_trade(self, symbol: str, side: str, quantity: float,
                       price: float) -> PreTradeCheckResult:
        """
        Perform pre-trade risk check.

        Args:
            symbol: Trading symbol (e.g., BTC-USDT)
            side: Order side (buy/sell)
            quantity: Order quantity
            price: Order price

        Returns:
            PreTradeCheckResult with approval status and metrics
        """
        start_time = time.perf_counter()
        self._checks_performed += 1

        with self._lock:
            # Check manual override first
            if self.config.manual_override:
                self._circuit_breaker_state = CircuitBreakerState.OK
                return PreTradeCheckResult(
                    approved=True,
                    message="Manual override active - all checks bypassed",
                    latency_ms=(time.perf_counter() - start_time) * 1000
                )

            # Check circuit breaker
            if self._circuit_breaker_state in (CircuitBreakerState.TRIPPED, CircuitBreakerState.MANUAL_HALT):
                self._checks_rejected += 1
                return PreTradeCheckResult(
                    approved=False,
                    message=f"Trading halted: {self._circuit_breaker_state.value}",
                    latency_ms=(time.perf_counter() - start_time) * 1000
                )

            # Calculate order value
            order_value = quantity * price
            position_pct = order_value / self._portfolio_value if self._portfolio_value > 0 else 0.0

            # Current metrics
            current_exposure = self._calculate_exposure(symbol)
            total_exposure = self._calculate_exposure()
            leverage = self._calculate_leverage()
            var_estimate = self._calculate_var()

            # 1. Check position size limit
            if position_pct > self.config.max_position_pct:
                adjusted_qty = (self._portfolio_value * self.config.max_position_pct) / price
                return PreTradeCheckResult(
                    approved=True,
                    message=f"Position size reduced from {quantity} to {adjusted_qty:.6f}",
                    adjusted_quantity=adjusted_qty,
                    adjustment_reason="position_size_limit",
                    var_estimate=var_estimate,
                    leverage_used=leverage,
                    exposure_pct=current_exposure,
                    latency_ms=(time.perf_counter() - start_time) * 1000
                )

            # 2. Check exposure limit
            if current_exposure + position_pct > self.config.max_single_exposure_pct:
                max_qty = (self._portfolio_value * (self.config.max_single_exposure_pct - current_exposure)) / price
                if max_qty > 0:
                    return PreTradeCheckResult(
                        approved=True,
                        message=f"Exposure limit - quantity reduced from {quantity} to {max_qty:.6f}",
                        adjusted_quantity=max_qty,
                        adjustment_reason="exposure_limit",
                        var_estimate=var_estimate,
                        leverage_used=leverage,
                        exposure_pct=current_exposure,
                        latency_ms=(time.perf_counter() - start_time) * 1000
                    )
                else:
                    self._checks_rejected += 1
                    return PreTradeCheckResult(
                        approved=False,
                        message=f"Exposure limit exceeded for {symbol}",
                        var_estimate=var_estimate,
                        leverage_used=leverage,
                        exposure_pct=current_exposure,
                        latency_ms=(time.perf_counter() - start_time) * 1000
                    )

            # 3. Check total exposure limit
            if total_exposure + position_pct > self.config.max_total_position_pct:
                self._checks_rejected += 1
                return PreTradeCheckResult(
                    approved=False,
                    message=f"Total exposure limit would be exceeded: {(total_exposure + position_pct)*100:.1f}%",
                    var_estimate=var_estimate,
                    leverage_used=leverage,
                    exposure_pct=current_exposure,
                    latency_ms=(time.perf_counter() - start_time) * 1000
                )

            # 4. Check VaR-based limit (only when we have return history)
            # VaR-based limit checks if projected position loss would exceed VaR threshold
            # We only apply this check when we have actual return data
            if len(self._returns_history) >= 2:
                var_threshold = self._portfolio_value * self.config.max_var_pct
                projected_var = position_pct * self._portfolio_value * 2  # Simple VaR projection
                if projected_var > var_threshold:
                    # Scale down position based on VaR
                    max_var_position = (var_threshold / 2) / price if price > 0 else quantity
                    if max_var_position < quantity:
                        return PreTradeCheckResult(
                            approved=True,
                            message=f"VaR limit - quantity reduced from {quantity} to {max_var_position:.6f}",
                            adjusted_quantity=max_var_position,
                            adjustment_reason="var_limit",
                            var_estimate=var_estimate,
                            leverage_used=leverage,
                            exposure_pct=current_exposure,
                            latency_ms=(time.perf_counter() - start_time) * 1000
                        )

            # 5. Check leverage
            if self._portfolio_value > 0:
                new_leverage = (leverage * self._portfolio_value + position_pct * self._portfolio_value) / self._portfolio_value
                if new_leverage > self.config.max_leverage_per_trade:
                    self._checks_rejected += 1
                    return PreTradeCheckResult(
                        approved=False,
                        message=f"Leverage limit exceeded: {new_leverage:.2f}x > {self.config.max_leverage_per_trade:.2f}x",
                        var_estimate=var_estimate,
                        leverage_used=leverage,
                        exposure_pct=current_exposure,
                        latency_ms=(time.perf_counter() - start_time) * 1000
                    )

            # 6. Check minimum order size
            if quantity < self.config.min_position_size:
                self._checks_rejected += 1
                return PreTradeCheckResult(
                    approved=False,
                    message=f"Order size below minimum: {quantity} < {self.config.min_position_size}",
                    var_estimate=var_estimate,
                    leverage_used=leverage,
                    exposure_pct=current_exposure,
                    latency_ms=(time.perf_counter() - start_time) * 1000
                )

            # All checks passed
            latency = (time.perf_counter() - start_time) * 1000
            self._total_latency_ms += latency

            return PreTradeCheckResult(
                approved=True,
                message="Pre-trade check passed",
                var_estimate=var_estimate,
                leverage_used=leverage,
                exposure_pct=current_exposure,
                latency_ms=latency
            )

    def record_post_trade(self, symbol: str, side: str, quantity: float,
                          price: float) -> PostTradeUpdate:
        """
        Record post-trade update for monitoring.

        Args:
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Order quantity
            price: Execution price

        Returns:
            PostTradeUpdate with updated risk metrics
        """
        with self._lock:
            # Update position
            current_price = price
            existing_pos = self._positions.get(symbol, {})
            existing_qty = existing_pos.get('quantity', 0.0)
            entry_price = existing_pos.get('entry_price', price)

            if side == "buy":
                new_qty = existing_qty + quantity
                if existing_qty == 0:
                    new_entry = price
                else:
                    new_entry = entry_price  # Keep original entry
            else:  # sell
                new_qty = existing_qty - quantity
                new_entry = entry_price

            if new_qty > 0:
                self.update_position(symbol, new_qty, new_entry, current_price)
            else:
                self.update_position(symbol, 0, 0, 0)

            # Calculate new metrics AFTER position update
            new_exposure = self._calculate_exposure(symbol)  # Now returns correct value
            new_leverage = self._calculate_leverage()

            # Update portfolio value (simplified - in real system this comes from exchange)
            trade_value = quantity * price
            if side == "buy":
                self._portfolio_value -= trade_value
            else:
                self._portfolio_value += trade_value

            return PostTradeUpdate(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                timestamp=datetime.now(),
                portfolio_value_after=self._portfolio_value,
                new_position_pct=new_exposure,
                new_exposure_pct=self._calculate_exposure(),
                new_leverage=new_leverage
            )

    def check_circuit_breakers(self) -> Tuple[CircuitBreakerState, Optional[RiskEvent]]:
        """
        Check if any circuit breakers should trigger.

        Returns:
            Tuple of (circuit_breaker_state, risk_event if triggered)
        """
        with self._lock:
            # Check manual halt
            if self.config.manual_override and self._manual_halt_reason:
                self._circuit_breaker_state = CircuitBreakerState.MANUAL_HALT
                return self._circuit_breaker_state, None

            # Check cooldown
            if self._circuit_breaker_state == CircuitBreakerState.TRIPPED:
                if self._circuit_breaker_triggered_at:
                    elapsed = (datetime.now() - self._circuit_breaker_triggered_at).total_seconds()
                    if elapsed < self.config.circuit_breaker_cooldown_secs:
                        return self._circuit_breaker_state, self._last_risk_event
                    else:
                        # Auto-reset after cooldown
                        self._circuit_breaker_state = CircuitBreakerState.OK
                        self._circuit_breaker_triggered_at = None
                        return self._circuit_breaker_state, self._last_risk_event

            # Calculate current metrics
            daily_dd, weekly_dd, monthly_dd = self._calculate_drawdown()

            # Check daily loss limit
            if self._daily_pnl < 0 and abs(self._daily_pnl) / self._daily_start_value > self.config.max_daily_loss_pct:
                event = RiskEvent(
                    event_type=RiskEventType.DRAWDOWN_EXCEEDED,
                    timestamp=datetime.now(),
                    message=f"Daily loss limit hit: {abs(self._daily_pnl)/self._daily_start_value*100:.2f}%",
                    value=abs(self._daily_pnl) / self._daily_start_value,
                    threshold=self.config.max_daily_loss_pct,
                    action_taken="trading_halted"
                )
                self._trigger_circuit_breaker(event)
                return self._circuit_breaker_state, event

            # Check weekly loss limit
            if self._weekly_pnl < 0 and abs(self._weekly_pnl) / self._weekly_start_value > self.config.max_weekly_loss_pct:
                event = RiskEvent(
                    event_type=RiskEventType.DRAWDOWN_EXCEEDED,
                    timestamp=datetime.now(),
                    message=f"Weekly loss limit hit: {abs(self._weekly_pnl)/self._weekly_start_value*100:.2f}%",
                    value=abs(self._weekly_pnl) / self._weekly_start_value,
                    threshold=self.config.max_weekly_loss_pct,
                    action_taken="trading_halted"
                )
                self._trigger_circuit_breaker(event)
                return self._circuit_breaker_state, event

            # Check monthly loss limit
            if self._monthly_pnl < 0 and abs(self._monthly_pnl) / self._monthly_start_value > self.config.max_monthly_loss_pct:
                event = RiskEvent(
                    event_type=RiskEventType.DRAWDOWN_EXCEEDED,
                    timestamp=datetime.now(),
                    message=f"Monthly loss limit hit: {abs(self._monthly_pnl)/self._monthly_start_value*100:.2f}%",
                    value=abs(self._monthly_pnl) / self._monthly_start_value,
                    threshold=self.config.max_monthly_loss_pct,
                    action_taken="trading_halted"
                )
                self._trigger_circuit_breaker(event)
                return self._circuit_breaker_state, event

            # Check consecutive losses
            if self._consecutive_losses >= self.config.consecutive_losses_threshold:
                event = RiskEvent(
                    event_type=RiskEventType.LOSS_LIMIT_EXCEEDED,
                    timestamp=datetime.now(),
                    message=f"Consecutive losses threshold hit: {self._consecutive_losses}",
                    value=self._consecutive_losses,
                    threshold=self.config.consecutive_losses_threshold,
                    action_taken="trading_halted"
                )
                self._trigger_circuit_breaker(event)
                return self._circuit_breaker_state, event

            # Check VaR limit
            var_value = self._calculate_var()
            if var_value > self._portfolio_value * self.config.max_var_pct:
                event = RiskEvent(
                    event_type=RiskEventType.VAR_EXCEEDED,
                    timestamp=datetime.now(),
                    message=f"VaR limit exceeded: {var_value/self._portfolio_value*100:.2f}%",
                    value=var_value / self._portfolio_value,
                    threshold=self.config.max_var_pct,
                    action_taken="trading_halted"
                )
                self._trigger_circuit_breaker(event)
                return self._circuit_breaker_state, event

            # Check leverage
            leverage = self._calculate_leverage()
            if leverage > self.config.max_leverage:
                event = RiskEvent(
                    event_type=RiskEventType.LEVERAGE_EXCEEDED,
                    timestamp=datetime.now(),
                    message=f"Leverage limit exceeded: {leverage:.2f}x",
                    value=leverage,
                    threshold=self.config.max_leverage,
                    action_taken="trading_halted"
                )
                self._trigger_circuit_breaker(event)
                return self._circuit_breaker_state, event

            return self._circuit_breaker_state, None

    def _trigger_circuit_breaker(self, event: RiskEvent):
        """Trigger circuit breaker with event."""
        if not self.config.enable_circuit_breaker:
            return

        self._circuit_breaker_state = CircuitBreakerState.TRIPPED
        self._circuit_breaker_triggered_at = datetime.now()
        self._last_risk_event = event
        self._risk_event_history.append(event)

    def manual_halt(self, reason: str):
        """
        Manually halt trading.

        Args:
            reason: Reason for manual halt
        """
        with self._lock:
            self._manual_halt_reason = reason
            self._circuit_breaker_state = CircuitBreakerState.MANUAL_HALT
            self._risk_event_history.append(RiskEvent(
                event_type=RiskEventType.MANUAL_HALT,
                timestamp=datetime.now(),
                message=f"Manual halt: {reason}",
                value=0.0,
                threshold=0.0,
                action_taken="manual_halt"
            ))

    def reset_circuit_breaker(self, reason: str = None):
        """
        Reset circuit breaker (manual reset).

        Args:
            reason: Optional reason for reset
        """
        with self._lock:
            self._circuit_breaker_state = CircuitBreakerState.OK
            self._circuit_breaker_triggered_at = None
            self._manual_halt_reason = None
            self._last_risk_event = None
            # Clear PnL tracking after manual reset to prevent immediate re-trip
            # User has acknowledged the condition and wants to resume trading
            self._daily_pnl = 0.0

    def get_risk_status(self) -> Dict[str, Any]:
        """Get comprehensive risk status."""
        with self._lock:
            daily_dd, weekly_dd, monthly_dd = self._calculate_drawdown()

            return {
                'portfolio_value': self._portfolio_value,
                'peak_value': self._peak_value,
                'daily_pnl': self._daily_pnl,
                'weekly_pnl': self._weekly_pnl,
                'monthly_pnl': self._monthly_pnl,
                'realized_pnl': self._realized_pnl,
                'unrealized_pnl': self._unrealized_pnl,
                'daily_drawdown': f"{daily_dd*100:.2f}%",
                'weekly_drawdown': f"{weekly_dd*100:.2f}%",
                'monthly_drawdown': f"{monthly_dd*100:.2f}%",
                'circuit_breaker_state': self._circuit_breaker_state.value,
                'leverage': self._calculate_leverage(),
                'total_exposure': f"{self._calculate_exposure()*100:.1f}%",
                'var_estimate': self._calculate_var(),
                'var_limit': f"{self.config.max_var_pct*100:.1f}%",
                'positions': len(self._positions),
                'consecutive_losses': self._consecutive_losses,
                'checks_performed': self._checks_performed,
                'checks_rejected': self._checks_rejected,
                'avg_latency_ms': self._total_latency_ms / self._checks_performed if self._checks_performed > 0 else 0,
                'recent_risk_events': [
                    {
                        'type': e.event_type.value,
                        'timestamp': e.timestamp.isoformat(),
                        'message': e.message
                    } for e in self._risk_event_history[-5:]
                ]
            }

    def get_exposures(self) -> Dict[str, float]:
        """Get current exposures by symbol."""
        with self._lock:
            return dict(self._exposures)

    def get_positions(self) -> Dict[str, Dict]:
        """Get current positions."""
        with self._lock:
            return dict(self._positions)