"""
Advanced Risk Controller with portfolio-level risk management.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math

@dataclass
class VaRResult:
    """Value at Risk calculation result."""
    var_95: float  # 95% VaR
    var_99: float  # 99% VaR
    expected_shortfall: float  # CVaR
    confidence_level: float

@dataclass
class ExposureLimit:
    """Exposure limit for a category."""
    max_exposure_pct: float
    current_exposure_pct: float
    category: str

class AdvancedRiskController:
    """
    Advanced risk controller with VaR and exposure monitoring.
    """

    def __init__(
        self,
        portfolio_value: float = 100000,
        var_confidence: float = 0.95,
    ):
        self.portfolio_value = portfolio_value
        self.var_confidence = var_confidence
        self._position_history: List[Dict] = []
        self._returns_history: List[float] = []
        self._exposures: Dict[str, float] = {}

    def calculate_var(self, returns: List[float], portfolio_value: float) -> VaRResult:
        """
        Calculate Value at Risk using historical method.
        """
        if not returns:
            return VaRResult(var_95=0, var_99=0, expected_shortfall=0, confidence_level=0.95)

        # Sort returns
        sorted_returns = sorted(returns)
        n = len(sorted_returns)

        # 95% VaR
        var_95_idx = int(n * 0.05)
        var_95 = abs(sorted_returns[var_95_idx]) * portfolio_value

        # 99% VaR
        var_99_idx = int(n * 0.01)
        var_99 = abs(sorted_returns[var_99_idx]) * portfolio_value

        # Expected Shortfall (CVaR)
        tail_returns = sorted_returns[:var_95_idx]
        expected_shortfall = abs(sum(tail_returns) / len(tail_returns)) * portfolio_value if tail_returns else 0

        return VaRResult(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall=expected_shortfall,
            confidence_level=self.var_confidence,
        )

    def record_return(self, return_pct: float):
        """Record a return for VaR calculation."""
        self._returns_history.append(return_pct)
        # Keep last 252 days (1 year of data)
        if len(self._returns_history) > 252:
            self._returns_history.pop(0)

    def set_exposure(self, category: str, exposure_pct: float):
        """Set exposure for a category (e.g., 'BTC', 'ETH', 'DeFi')."""
        self._exposures[category] = exposure_pct

    def check_exposure_limits(self, limits: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        Check if exposures are within limits.

        Args:
            limits: Dict of category -> max_exposure_pct

        Returns:
            (all_within_limits, list_of_violations)
        """
        violations = []
        for category, max_exposure in limits.items():
            current = self._exposures.get(category, 0)
            if current > max_exposure:
                violations.append(f"{category}: {current*100:.1f}% > {max_exposure*100:.1f}%")

        return len(violations) == 0, violations

    def calculate_portfolio_volatility(self) -> float:
        """Calculate portfolio volatility (annualized)."""
        if len(self._returns_history) < 2:
            return 0.0

        mean_return = sum(self._returns_history) / len(self._returns_history)
        variance = sum((r - mean_return) ** 2 for r in self._returns_history) / len(self._returns_history)
        std_dev = math.sqrt(variance)

        # Annualize (assuming daily returns)
        return std_dev * math.sqrt(252)

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if len(self._returns_history) < 2:
            return 0.0

        mean_return = sum(self._returns_history) / len(self._returns_history)
        std_dev = self.calculate_portfolio_volatility()

        if std_dev == 0:
            return 0.0

        annualized_return = mean_return * 252
        return (annualized_return - risk_free_rate) / std_dev

    def get_risk_report(self) -> Dict:
        """Get comprehensive risk report."""
        var_result = self.calculate_var(self._returns_history, self.portfolio_value)

        return {
            'portfolio_value': self.portfolio_value,
            'volatility': self.calculate_portfolio_volatility(),
            'sharpe_ratio': self.calculate_sharpe_ratio(),
            'var_95': var_result.var_95,
            'var_99': var_result.var_99,
            'expected_shortfall': var_result.expected_shortfall,
            'exposures': self._exposures,
            'data_points': len(self._returns_history),
        }