"""
AI Auto-Iteration Module for strategy optimization.

Components:
- strategy_generator: Generate strategies from natural language
- backtest_runner: Run backtests and collect metrics
- metrics_evaluator: Evaluate strategy metrics
- parameter_optimizer: Optimize strategy parameters
- iteration_loop: Main iteration manager
"""

from .strategy_generator import StrategyGenerator
from .metrics_evaluator import MetricsEvaluator, StrategyMetrics
from .iteration_loop import IterationLoop

__all__ = ["StrategyGenerator", "MetricsEvaluator", "StrategyMetrics", "IterationLoop"]
