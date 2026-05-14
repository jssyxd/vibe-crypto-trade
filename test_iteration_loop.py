#!/usr/bin/env python3
"""
Test script for AI Auto-Iteration Loop.

Tests:
1. Strategy generation
2. Backtest running
3. Metrics evaluation
4. Parameter optimization
5. Full iteration loop
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from iteration import StrategyGenerator, MetricsEvaluator, IterationLoop
from iteration.strategy_generator import StrategySpec
from iteration.metrics_evaluator import StrategyMetrics, EvaluationResult


def test_strategy_generator():
    """Test strategy generation."""
    print("\n" + "="*60)
    print("Testing Strategy Generator")
    print("="*60)

    gen = StrategyGenerator()
    
    # List templates
    templates = gen.list_templates()
    print(f"Available templates: {templates}")
    
    # Get template info
    info = gen.get_template_info("rsi_mean_reversion")
    print(f"\nRSI Strategy info:")
    print(f"  Description: {info['description']}")
    print(f"  Parameters: {info['parameters']}")
    
    # Generate strategy
    spec = gen.generate("rsi_mean_reversion", {"rsi_period": 14, "oversold": 30, "overbought": 70})
    print(f"\nGenerated strategy:")
    print(f"  Name: {spec.name}")
    print(f"  Parameters: {spec.parameters}")
    print(f"  Code preview: {spec.code[:200]}...")
    
    return True


def test_metrics_evaluator():
    """Test metrics evaluation."""
    print("\n" + "="*60)
    print("Testing Metrics Evaluator")
    print("="*60)

    evaluator = MetricsEvaluator()
    
    # Good metrics
    good_metrics = StrategyMetrics(
        final_value=120000,
        total_return=0.20,
        annual_return=0.10,
        sharpe=1.5,
        max_drawdown=-0.15,
        win_rate=0.60,
        trade_count=20,
        profit_factor=1.5,
        sortino=1.2,
        calmar=0.8,
    )
    
    result = evaluator.evaluate(good_metrics)
    print(f"Good metrics evaluation: {'PASSED' if result.passed else 'FAILED'}")
    print(f"  Overall score: {result.overall_score:.2f}")
    print(f"  Sharpe: {good_metrics.sharpe:.2f} - {'✓' if result.checks[0]['passed'] else '✗'}")
    
    # Poor metrics
    poor_metrics = StrategyMetrics(
        final_value=80000,
        total_return=-0.20,
        annual_return=-0.10,
        sharpe=0.3,
        max_drawdown=-0.40,
        win_rate=0.35,
        trade_count=5,
        profit_factor=0.8,
        sortino=0.2,
        calmar=-0.2,
    )
    
    result = evaluator.evaluate(poor_metrics)
    print(f"\nPoor metrics evaluation: {'PASSED' if result.passed else 'FAILED'}")
    print(f"  Overall score: {result.overall_score:.2f}")
    
    # Get improvement hints
    hints = evaluator.get_improvement_hints(poor_metrics)
    print(f"\nImprovement hints:")
    for hint in hints:
        print(f"  - {hint}")
    
    return True


def test_iteration_loop():
    """Test full iteration loop (short version)."""
    print("\n" + "="*60)
    print("Testing Iteration Loop (3 iterations)")
    print("="*60)

    # Create iteration loop with just 3 iterations for testing
    loop = IterationLoop(
        template_name="rsi_mean_reversion",
        max_iterations=3,
        base_dir="runs/test_optimization",
    )
    
    # Run optimization
    result = loop.optimize(
        symbol="BTC-USDT",
        start_date="2025-01-01",
        end_date="2026-05-14",
        initial_cash=100000,
    )
    
    print(f"\nOptimization result:")
    print(f"  Success: {result.success}")
    print(f"  Message: {result.message}")
    print(f"  Best Iteration: {result.best_iteration}")
    print(f"  Total Iterations: {result.total_iterations}")
    
    if result.best_spec:
        print(f"  Best Parameters: {result.best_spec.parameters}")
        print(f"  Best Sharpe: {result.best_metrics.sharpe:.3f}")
        print(f"  Best Win Rate: {result.best_metrics.win_rate*100:.1f}%")
        print(f"  Best Max DD: {result.best_metrics.max_drawdown*100:.1f}%")
    
    # Save results
    loop.save_results("test_optimization_results.json")
    
    return True


def main():
    print("="*60)
    print("Vibe-Crypto-Trading AI Auto-Iteration Test")
    print("="*60)

    tests = [
        ("Strategy Generator", test_strategy_generator),
        ("Metrics Evaluator", test_metrics_evaluator),
        ("Iteration Loop", test_iteration_loop),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"\n❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, f"FAIL: {e}"))

    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    for name, result in results:
        status = "✅" if "PASS" in result else "❌"
        print(f"{status} {name}: {result}")

    all_passed = all("PASS" in r for _, r in results)
    print("\n" + ("✅ ALL TESTS PASSED!" if all_passed else "❌ SOME TESTS FAILED"))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
