"""
Multi-Strategy Portfolio Manager.
Manages multiple trading strategies with capital allocation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json


class AllocationStrategy(Enum):
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MOMENTUM_WEIGHTED = "momentum_weighted"


@dataclass
class StrategyPosition:
    strategy_name: str
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    allocation_pct: float


@dataclass
class PortfolioStats:
    total_value: float
    cash: float
    total_pnl: float
    day_pnl: float
    positions: List[StrategyPosition]
    strategy_allocations: Dict[str, float]


class PortfolioManager:
    """
    Manages multiple trading strategies.
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        max_strategies: int = 5,
        allocation_strategy: AllocationStrategy = AllocationStrategy.EQUAL_WEIGHT,
    ):
        self.initial_capital = initial_capital
        self.max_strategies = max_strategies
        self.allocation_strategy = allocation_strategy
        self.cash = initial_capital
        self._positions: Dict[str, StrategyPosition] = {}
        self._strategy_returns: Dict[str, List[float]] = {}
        self._strategy_allocations: Dict[str, float] = {}

    def add_strategy_allocation(self, strategy_name: str, allocation_pct: float) -> bool:
        """Add or update strategy allocation."""
        if allocation_pct > 1.0 or allocation_pct < 0:
            return False
        if len(self._strategy_allocations) >= self.max_strategies and strategy_name not in self._strategy_allocations:
            return False
        self._strategy_allocations[strategy_name] = allocation_pct
        return True

    def calculate_rebalance(self) -> Dict[str, float]:
        """Calculate rebalancing amounts for each strategy."""
        allocations = {}
        # Equal weight: 1/max_strategies for each
        if self.allocation_strategy == AllocationStrategy.EQUAL_WEIGHT:
            weight = 1.0 / max(1, len(self._strategy_allocations))
            for strategy in self._strategy_allocations.keys():
                allocations[strategy] = weight
        # Risk parity: equal risk contribution (simplified)
        elif self.allocation_strategy == AllocationStrategy.RISK_PARITY:
            # Simplified: use inverse of variance as weight
            for strategy in self._strategy_allocations.keys():
                returns = self._strategy_returns.get(strategy, [])
                if len(returns) >= 2:
                    variance = sum((r - sum(returns) / len(returns)) ** 2 for r in returns) / len(returns)
                    allocations[strategy] = 1.0 / (variance + 1e-10)
                else:
                    allocations[strategy] = 1.0 / len(self._strategy_allocations)
            # Normalize
            total = sum(allocations.values())
            if total > 0:
                for k in allocations:
                    allocations[k] /= total
        # Momentum weighted: weight by recent performance
        elif self.allocation_strategy == AllocationStrategy.MOMENTUM_WEIGHTED:
            weights = {}
            for strategy in self._strategy_allocations.keys():
                returns = self._strategy_returns.get(strategy, [])
                if len(returns) >= 3:
                    # Use last 3 returns for momentum
                    momentum = sum(returns[-3:]) / 3
                    weights[strategy] = max(0.01, momentum + 1)  # Shift to positive
                else:
                    weights[strategy] = 0.01
            total = sum(weights.values())
            if total > 0:
                for k in weights:
                    allocations[k] = weights[k] / total
            else:
                weight = 1.0 / max(1, len(self._strategy_allocations))
                for strategy in self._strategy_allocations.keys():
                    allocations[strategy] = weight
        return allocations

    def get_portfolio_stats(self) -> PortfolioStats:
        """Get current portfolio statistics."""
        positions = list(self._positions.values())
        total_value = self.cash + sum(p.unrealized_pnl for p in positions)

        return PortfolioStats(
            total_value=total_value,
            cash=self.cash,
            total_pnl=total_value - self.initial_capital,
            day_pnl=0.0,  # Would calculate from daily change
            positions=positions,
            strategy_allocations=dict(self._strategy_allocations),
        )

    def record_strategy_return(self, strategy_name: str, return_pct: float):
        """Record strategy return for correlation/risk calculations."""
        if strategy_name not in self._strategy_returns:
            self._strategy_returns[strategy_name] = []
        self._strategy_returns[strategy_name].append(return_pct)

    def get_strategy_correlation(self, strategy1: str, strategy2: str) -> float:
        """Calculate correlation between two strategies."""
        if strategy1 not in self._strategy_returns or strategy2 not in self._strategy_returns:
            return 0.0

        returns1 = self._strategy_returns[strategy1]
        returns2 = self._strategy_returns[strategy2]

        if len(returns1) < 2 or len(returns2) < 2:
            return 0.0

        # Simple correlation calculation
        mean1 = sum(returns1) / len(returns1)
        mean2 = sum(returns2) / len(returns2)

        numerator = sum((r1 - mean1) * (r2 - mean2) for r1, r2 in zip(returns1, returns2))
        denom1 = sum((r - mean1) ** 2 for r in returns1) ** 0.5
        denom2 = sum((r - mean2) ** 2 for r in returns2) ** 0.5

        if denom1 * denom2 == 0:
            return 0.0

        return numerator / (denom1 * denom2)

    def add_position(
        self,
        strategy_name: str,
        symbol: str,
        quantity: float,
        entry_price: float,
    ) -> bool:
        """Add a new position for a strategy."""
        position_key = f"{strategy_name}_{symbol}"
        cost = quantity * entry_price

        if cost > self.cash:
            return False

        self._positions[position_key] = StrategyPosition(
            strategy_name=strategy_name,
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            unrealized_pnl=0.0,
            allocation_pct=0.0,
        )
        self.cash -= cost
        return True

    def update_position_price(self, strategy_name: str, symbol: str, current_price: float):
        """Update the current price of a position."""
        position_key = f"{strategy_name}_{symbol}"
        if position_key in self._positions:
            position = self._positions[position_key]
            position.current_price = current_price
            position.unrealized_pnl = (current_price - position.entry_price) * position.quantity

    def remove_position(self, strategy_name: str, symbol: str) -> bool:
        """Remove a position and return proceeds to cash."""
        position_key = f"{strategy_name}_{symbol}"
        if position_key in self._positions:
            position = self._positions[position_key]
            proceeds = position.current_price * position.quantity
            self.cash += proceeds
            del self._positions[position_key]
            return True
        return False

    def get_strategy_positions(self, strategy_name: str) -> List[StrategyPosition]:
        """Get all positions for a specific strategy."""
        return [p for p in self._positions.values() if p.strategy_name == strategy_name]