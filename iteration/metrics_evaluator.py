"""Metrics Evaluator for strategy performance assessment."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import json


@dataclass
class StrategyMetrics:
    """Strategy performance metrics."""
    final_value: float
    total_return: float
    annual_return: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    trade_count: int
    profit_factor: float = 0.0
    sortino: float = 0.0
    calmar: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'final_value': self.final_value,
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'sharpe': self.sharpe,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'trade_count': self.trade_count,
            'profit_factor': self.profit_factor,
            'sortino': self.sortino,
            'calmar': self.calmar,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'StrategyMetrics':
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_backtest_result(cls, result: dict) -> 'StrategyMetrics':
        """Create metrics from backtest result JSON."""
        return cls(
            final_value=result.get('final_value', 0),
            total_return=result.get('total_return', 0),
            annual_return=result.get('annual_return', 0),
            sharpe=result.get('sharpe', 0),
            max_drawdown=result.get('max_drawdown', 0),
            win_rate=result.get('win_rate', 0),
            trade_count=result.get('trade_count', 0),
            profit_factor=result.get('profit_factor', 0),
            sortino=result.get('sortino', 0),
            calmar=result.get('calmar', 0),
        )


class MetricsEvaluator:
    """
    Evaluates strategy metrics against defined thresholds.
    
    Default thresholds:
    - Sharpe Ratio: > 1.0 (good), > 1.5 (excellent)
    - Max Drawdown: < 20% 
    - Win Rate: > 50%
    - Trade Count: >= 10 (statistically significant)
    """

    def __init__(
        self,
        min_sharpe: float = 1.0,
        max_drawdown: float = 0.20,
        min_win_rate: float = 0.50,
        min_trade_count: int = 10,
        min_profit_factor: float = 1.2,
    ):
        self.min_sharpe = min_sharpe
        self.max_drawdown = max_drawdown
        self.min_win_rate = min_win_rate
        self.min_trade_count = min_trade_count
        self.min_profit_factor = min_profit_factor

    def evaluate(self, metrics: StrategyMetrics) -> 'EvaluationResult':
        """
        Evaluate metrics against thresholds.
        
        Returns:
            EvaluationResult with pass/fail and details
        """
        checks = []
        all_passed = True
        
        # Sharpe ratio check
        sharpe_pass = metrics.sharpe >= self.min_sharpe
        checks.append({
            'metric': 'sharpe',
            'value': metrics.sharpe,
            'threshold': f">= {self.min_sharpe}",
            'passed': sharpe_pass,
            'weight': 2.0,  # Higher weight for Sharpe
        })
        if not sharpe_pass:
            all_passed = False
        
        # Max drawdown check
        dd_pass = abs(metrics.max_drawdown) <= self.max_drawdown
        checks.append({
            'metric': 'max_drawdown',
            'value': metrics.max_drawdown,
            'threshold': f"<= {self.max_drawdown*100}%",
            'passed': dd_pass,
            'weight': 2.0,
        })
        if not dd_pass:
            all_passed = False
        
        # Win rate check
        wr_pass = metrics.win_rate >= self.min_win_rate
        checks.append({
            'metric': 'win_rate',
            'value': metrics.win_rate,
            'threshold': f">= {self.min_win_rate*100}%",
            'passed': wr_pass,
            'weight': 1.0,
        })
        if not wr_pass:
            all_passed = False
        
        # Trade count check
        tc_pass = metrics.trade_count >= self.min_trade_count
        checks.append({
            'metric': 'trade_count',
            'value': metrics.trade_count,
            'threshold': f">= {self.min_trade_count}",
            'passed': tc_pass,
            'weight': 1.0,
        })
        if not tc_pass:
            all_passed = False
        
        # Profit factor check
        pf_pass = metrics.profit_factor >= self.min_profit_factor
        checks.append({
            'metric': 'profit_factor',
            'value': metrics.profit_factor,
            'threshold': f">= {self.min_profit_factor}",
            'passed': pf_pass,
            'weight': 1.0,
        })
        if not pf_pass:
            all_passed = False
        
        # Calculate overall score (weighted)
        total_weight = sum(c['weight'] for c in checks)
        passed_weight = sum(c['weight'] * (1 if c['passed'] else 0) for c in checks)
        overall_score = passed_weight / total_weight if total_weight > 0 else 0
        
        return EvaluationResult(
            passed=all_passed,
            overall_score=overall_score,
            checks=checks,
            metrics=metrics,
        )

    def get_improvement_hints(self, metrics: StrategyMetrics) -> list:
        """Get suggestions for improving the strategy."""
        hints = []
        
        if metrics.sharpe < self.min_sharpe:
            hints.append(f"Sharpe ratio too low ({metrics.sharpe:.2f} < {self.min_sharpe}). Consider adjusting entry/exit timing.")
        
        if abs(metrics.max_drawdown) > self.max_drawdown:
            hints.append(f"Max drawdown too high ({abs(metrics.max_drawdown)*100:.1f}% > {self.max_drawdown*100}%). Add stop-loss or reduce position size.")
        
        if metrics.win_rate < self.min_win_rate:
            hints.append(f"Win rate too low ({metrics.win_rate*100:.1f}% < {self.min_win_rate*100}%). Try adjusting indicators or timeframes.")
        
        if metrics.trade_count < self.min_trade_count:
            hints.append(f"Too few trades ({metrics.trade_count}). Consider shorter timeframe or wider entry conditions.")
        
        if metrics.profit_factor < self.min_profit_factor:
            hints.append(f"Profit factor too low ({metrics.profit_factor:.2f} < {self.min_profit_factor}). Improve risk/reward ratio.")
        
        return hints


@dataclass
class EvaluationResult:
    """Result of metrics evaluation."""
    passed: bool
    overall_score: float
    checks: list
    metrics: StrategyMetrics
    
    def to_dict(self) -> dict:
        return {
            'passed': self.passed,
            'overall_score': self.overall_score,
            'checks': self.checks,
            'metrics': self.metrics.to_dict(),
        }
