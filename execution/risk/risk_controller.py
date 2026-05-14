"""Risk Controller for trading risk management."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum


class CircuitBreakerStatus(Enum):
    OK = "ok"
    WARNING = "warning"
    TRIPPED = "tripped"


@dataclass
class RiskLimits:
    """Risk limit configuration."""
    max_position_pct: float = 0.1  # Max 10% of portfolio per trade
    max_leverage: float = 1.0  # No leverage by default
    max_drawdown_daily: float = 0.05  # Max 5% daily drawdown
    max_drawdown_weekly: float = 0.10  # Max 10% weekly drawdown
    max_drawdown_monthly: float = 0.20  # Max 20% monthly drawdown
    max_total_positions: int = 5  # Max 5 open positions


@dataclass
class RiskMetrics:
    """Current risk metrics."""
    portfolio_value: float = 100000.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0
    daily_drawdown: float = 0.0
    weekly_drawdown: float = 0.0
    monthly_drawdown: float = 0.0
    peak_value: float = 100000.0
    current_positions: int = 0


@dataclass
class RiskCheckResult:
    """Result of risk check."""
    approved: bool
    message: str
    breaker_status: CircuitBreakerStatus = CircuitBreakerStatus.OK
    adjustments: Dict = field(default_factory=dict)


class RiskController:
    """
    Risk Controller for trading risk management.

    Implements:
    - Position size limits
    - Leverage limits
    - Drawdown circuit breakers (daily/weekly/monthly)
    """

    def __init__(self, limits: Optional[RiskLimits] = None):
        """
        Initialize Risk Controller.

        Args:
            limits: Risk limit configuration
        """
        self.limits = limits or RiskLimits()
        self.metrics = RiskMetrics()
        self._peak_value = 100000.0
        self._daily_start_value = 100000.0
        self._weekly_start_value = 100000.0
        self._monthly_start_value = 100000.0
        self._last_reset_date = datetime.now().date()
        self._trade_log: List[Dict] = []

    def update_metrics(self, portfolio_value: float, positions: Dict[str, float]):
        """Update current risk metrics."""
        self.metrics.portfolio_value = portfolio_value
        self.metrics.current_positions = len(positions)

        # Update peak value
        if portfolio_value > self._peak_value:
            self._peak_value = portfolio_value
            self.metrics.peak_value = self._peak_value

        # Calculate drawdowns
        self.metrics.daily_drawdown = (self._peak_value - portfolio_value) / self._peak_value
        self.metrics.weekly_drawdown = (self._weekly_start_value - portfolio_value) / self._weekly_start_value
        self.metrics.monthly_drawdown = (self._monthly_start_value - portfolio_value) / self._monthly_start_value

        # Check if we need to reset period start values
        self._check_period_reset()

    def _check_period_reset(self):
        """Check if period start values need reset."""
        now = datetime.now().date()

        # Reset daily at midnight
        if now > self._last_reset_date:
            self._daily_start_value = self.metrics.portfolio_value
            self.metrics.daily_pnl = 0.0

        # Reset weekly on Monday
        if now.weekday() == 0 and now != self._last_reset_date:
            self._weekly_start_value = self.metrics.portfolio_value
            self.metrics.weekly_pnl = 0.0

        # Reset monthly on 1st
        if now.day == 1 and now != self._last_reset_date:
            self._monthly_start_value = self.metrics.portfolio_value
            self.metrics.monthly_pnl = 0.0

        self._last_reset_date = now

    def check_order(self, symbol: str, side: str, quantity: float,
                    price: float, portfolio_value: float) -> RiskCheckResult:
        """
        Check if order passes risk controls.

        Args:
            symbol: Trading symbol (e.g., BTC-USDT)
            side: Order side (buy/sell)
            quantity: Order quantity
            price: Order price
            portfolio_value: Current portfolio value

        Returns:
            RiskCheckResult with approval status and message
        """
        self.update_metrics(portfolio_value, {})

        # Check circuit breaker
        if self.metrics.daily_drawdown >= self.limits.max_drawdown_daily:
            return RiskCheckResult(
                approved=False,
                message=f"Daily drawdown limit hit: {self.metrics.daily_drawdown*100:.2f}%",
                breaker_status=CircuitBreakerStatus.TRIPPED,
            )

        if self.metrics.weekly_drawdown >= self.limits.max_drawdown_weekly:
            return RiskCheckResult(
                approved=False,
                message=f"Weekly drawdown limit hit: {self.metrics.weekly_drawdown*100:.2f}%",
                breaker_status=CircuitBreakerStatus.TRIPPED,
            )

        if self.metrics.monthly_drawdown >= self.limits.max_drawdown_monthly:
            return RiskCheckResult(
                approved=False,
                message=f"Monthly drawdown limit hit: {self.metrics.monthly_drawdown*100:.2f}%",
                breaker_status=CircuitBreakerStatus.TRIPPED,
            )

        # Check position count
        if self.metrics.current_positions >= self.limits.max_total_positions:
            return RiskCheckResult(
                approved=False,
                message=f"Max positions reached: {self.metrics.current_positions}",
                breaker_status=CircuitBreakerStatus.WARNING,
            )

        # Check position size
        order_value = quantity * price
        position_pct = order_value / portfolio_value

        if position_pct > self.limits.max_position_pct:
            # Adjust quantity to fit limit
            max_qty = (portfolio_value * self.limits.max_position_pct) / price
            return RiskCheckResult(
                approved=True,
                message=f"Position size reduced from {quantity} to {max_qty:.6f}",
                breaker_status=CircuitBreakerStatus.OK,
                adjustments={'quantity': max_qty, 'reason': 'position_size_limit'},
            )

        return RiskCheckResult(
            approved=True,
            message="Order approved",
            breaker_status=CircuitBreakerStatus.OK,
        )

    def get_status(self) -> Dict:
        """Get current risk status."""
        return {
            'portfolio_value': self.metrics.portfolio_value,
            'peak_value': self._peak_value,
            'daily_drawdown': f"{self.metrics.daily_drawdown*100:.2f}%",
            'weekly_drawdown': f"{self.metrics.weekly_drawdown*100:.2f}%",
            'monthly_drawdown': f"{self.metrics.monthly_drawdown*100:.2f}%",
            'current_positions': self.metrics.current_positions,
            'max_positions': self.limits.max_total_positions,
            'daily_limit': f"{self.limits.max_drawdown_daily*100:.1f}%",
            'weekly_limit': f"{self.limits.max_drawdown_weekly*100:.1f}%",
            'monthly_limit': f"{self.limits.max_drawdown_monthly*100:.1f}%",
        }
