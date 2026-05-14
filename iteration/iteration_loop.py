"""Iteration Loop - main orchestration for strategy optimization."""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .strategy_generator import StrategyGenerator, StrategySpec
from .metrics_evaluator import MetricsEvaluator, StrategyMetrics, EvaluationResult
from .parameter_optimizer import ParameterOptimizer, ParameterRange


@dataclass
class IterationResult:
    """Result of a single iteration."""
    iteration: int
    strategy_spec: StrategySpec
    metrics: StrategyMetrics
    evaluation: EvaluationResult
    passed: bool
    run_dir: str
    error: Optional[str] = None


@dataclass
class OptimizationResult:
    """Final result of optimization."""
    success: bool
    best_iteration: int
    best_spec: StrategySpec
    best_metrics: StrategyMetrics
    iterations: List[IterationResult]
    total_iterations: int
    message: str


class IterationLoop:
    """
    Main iteration loop for strategy optimization.
    
    Workflow:
    1. Generate strategy with initial parameters
    2. Run backtest
    3. Evaluate metrics against thresholds
    4. If failed: adjust parameters and retry
    5. If passed or max iterations: return best result
    """

    def __init__(
        self,
        template_name: str,
        max_iterations: int = 5,
        evaluator: Optional[MetricsEvaluator] = None,
        base_dir: str = "runs/optimization",
    ):
        """
        Initialize Iteration Loop.
        
        Args:
            template_name: Strategy template to optimize
            max_iterations: Maximum optimization iterations
            evaluator: Metrics evaluator (uses defaults if None)
            base_dir: Base directory for run outputs
        """
        self.template_name = template_name
        self.max_iterations = max_iterations
        self.evaluator = evaluator or MetricsEvaluator()
        self.base_dir = base_dir
        
        self.generator = StrategyGenerator()
        self.optimizer = ParameterOptimizer(
            search_strategy="bayesian",
            max_iterations=max_iterations,
        )
        
        # Get parameter ranges from template
        template_info = self.generator.get_template_info(template_name)
        self.param_ranges = {}
        
        if template_info:
            for param_name, param_info in template_info['parameters'].items():
                self.param_ranges[param_name] = ParameterRange(
                    name=param_name,
                    param_type=param_info['type'],
                    current=param_info['default'],
                    min_value=param_info['min'],
                    max_value=param_info['max'],
                    step=param_info.get('step', 1.0 if param_info['type'] == 'int' else 0.1),
                )
        
        self.results: List[IterationResult] = []
        self.start_time: Optional[datetime] = None

    def optimize(
        self,
        symbol: str = "BTC-USDT",
        start_date: str = "2024-01-01",
        end_date: str = "2026-05-14",
        initial_cash: float = 100000,
    ) -> OptimizationResult:
        """
        Run optimization loop.
        
        Args:
            symbol: Trading symbol
            start_date: Backtest start date
            end_date: Backtest end date
            initial_cash: Initial capital
            
        Returns:
            OptimizationResult with best strategy found
        """
        self.start_time = datetime.now()
        self.results = []
        
        print("="*60)
        print(f"Starting Optimization: {self.template_name}")
        print(f"Symbol: {symbol}, Period: {start_date} to {end_date}")
        print(f"Max Iterations: {self.max_iterations}")
        print("="*60)
        
        best_result: Optional[IterationResult] = None
        current_params = {
            name: pr.current for name, pr in self.param_ranges.items()
        }
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n--- Iteration {iteration}/{self.max_iterations} ---")
            print(f"Parameters: {current_params}")
            
            try:
                # Generate strategy
                spec = self.generator.generate(self.template_name, current_params)
                
                # Save strategy to run directory
                run_dir = os.path.join(
                    self.base_dir,
                    f"{self.template_name}_iter{iteration}"
                )
                
                config_overrides = {
                    "codes": [symbol],
                    "start_date": start_date,
                    "end_date": end_date,
                    "initial_cash": initial_cash,
                }
                
                self.generator.save_strategy(spec, run_dir, config_overrides)
                
                # Run backtest
                print(f"Running backtest...")
                backtest_result = self.generator.run_backtest(run_dir)
                
                if backtest_result.get('status') != 'ok':
                    error = backtest_result.get('error', 'Unknown error')
                    print(f"❌ Backtest failed: {error}")
                    
                    result = IterationResult(
                        iteration=iteration,
                        strategy_spec=spec,
                        metrics=StrategyMetrics(
                            final_value=0, total_return=0, annual_return=0,
                            sharpe=0, max_drawdown=0, win_rate=0, trade_count=0
                        ),
                        evaluation=EvaluationResult(
                            passed=False, overall_score=0, checks=[], metrics=StrategyMetrics(
                                final_value=0, total_return=0, annual_return=0,
                                sharpe=0, max_drawdown=0, win_rate=0, trade_count=0
                            )
                        ),
                        passed=False,
                        run_dir=run_dir,
                        error=error,
                    )
                    self.results.append(result)
                    self.optimizer.record_result(current_params, 0)
                    continue
                
                # Parse metrics
                stdout = backtest_result.get('stdout', '{}')
                if isinstance(stdout, str):
                    metrics_dict = json.loads(stdout)
                else:
                    metrics_dict = stdout
                
                metrics = StrategyMetrics.from_backtest_result(metrics_dict)
                
                # Evaluate
                evaluation = self.evaluator.evaluate(metrics)
                
                print(f"Metrics:")
                print(f"  Sharpe:    {metrics.sharpe:.3f}")
                print(f"  Win Rate:  {metrics.win_rate*100:.1f}%")
                print(f"  Max DD:    {metrics.max_drawdown*100:.1f}%")
                print(f"  Trades:    {metrics.trade_count}")
                print(f"  Score:     {evaluation.overall_score:.2f}")
                print(f"  {'✅ PASSED' if evaluation.passed else '❌ FAILED'}")
                
                # Record result
                result = IterationResult(
                    iteration=iteration,
                    strategy_spec=spec,
                    metrics=metrics,
                    evaluation=evaluation,
                    passed=evaluation.passed,
                    run_dir=run_dir,
                )
                self.results.append(result)
                
                # Record for optimizer
                self.optimizer.record_result(
                    current_params,
                    evaluation.overall_score,
                    metrics.to_dict(),
                )
                
                # Update best
                if best_result is None or evaluation.overall_score > best_result.evaluation.overall_score:
                    best_result = result
                    print(f"🏆 New best!")
                
                # If passed, we can stop (found good strategy)
                if evaluation.passed:
                    print(f"✅ Strategy passed thresholds! Stopping early.")
                    break
                
                # Adjust parameters for next iteration
                if iteration < self.max_iterations:
                    current_params = self.optimizer.suggest_parameters(
                        current_params,
                        self.param_ranges,
                        iteration,
                    )
                
            except Exception as e:
                print(f"❌ Iteration failed: {e}")
                import traceback
                traceback.print_exc()
                
                result = IterationResult(
                    iteration=iteration,
                    strategy_spec=None,
                    metrics=StrategyMetrics(
                        final_value=0, total_return=0, annual_return=0,
                        sharpe=0, max_drawdown=0, win_rate=0, trade_count=0
                    ),
                    evaluation=EvaluationResult(
                        passed=False, overall_score=0, checks=[], metrics=StrategyMetrics(
                            final_value=0, total_return=0, annual_return=0,
                            sharpe=0, max_drawdown=0, win_rate=0, trade_count=0
                        )
                    ),
                    passed=False,
                    run_dir="",
                    error=str(e),
                )
                self.results.append(result)
        
        # Final summary
        print("\n" + "="*60)
        print("OPTIMIZATION COMPLETE")
        print("="*60)
        
        if best_result:
            print(f"Best Iteration: {best_result.iteration}")
            print(f"Best Score: {best_result.evaluation.overall_score:.3f}")
            print(f"Best Parameters: {best_result.strategy_spec.parameters}")
            print(f"Best Metrics:")
            print(f"  Sharpe:    {best_result.metrics.sharpe:.3f}")
            print(f"  Win Rate:  {best_result.metrics.win_rate*100:.1f}%")
            print(f"  Max DD:    {best_result.metrics.max_drawdown*100:.1f}%")
            print(f"  Trades:    {best_result.metrics.trade_count}")
        
        return OptimizationResult(
            success=best_result.evaluation.passed if best_result else False,
            best_iteration=best_result.iteration if best_result else 0,
            best_spec=best_result.strategy_spec if best_result else None,
            best_metrics=best_result.metrics if best_result else None,
            iterations=self.results,
            total_iterations=len(self.results),
            message="Success" if best_result and best_result.evaluation.passed else "Max iterations reached",
        )

    def save_results(self, output_path: str = "iteration_results.json"):
        """Save optimization results to JSON file."""
        results_data = {
            'template_name': self.template_name,
            'max_iterations': self.max_iterations,
            'total_iterations': len(self.results),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': datetime.now().isoformat(),
            'best_result': None,
            'all_iterations': [],
        }
        
        if self.results:
            best = max(self.results, key=lambda x: x.evaluation.overall_score)
            results_data['best_result'] = {
                'iteration': best.iteration,
                'passed': best.passed,
                'score': best.evaluation.overall_score,
                'metrics': best.metrics.to_dict(),
                'parameters': best.strategy_spec.parameters if best.strategy_spec else {},
                'run_dir': best.run_dir,
            }
            
            results_data['all_iterations'] = [
                {
                    'iteration': r.iteration,
                    'passed': r.passed,
                    'score': r.evaluation.overall_score,
                    'metrics': r.metrics.to_dict(),
                    'parameters': r.strategy_spec.parameters if r.strategy_spec else {},
                    'error': r.error,
                }
                for r in self.results
            ]
        
        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\nResults saved to: {output_path}")
