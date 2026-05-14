#!/usr/bin/env python3
"""
Simple script to run Vibe-Trading backtests.

Usage:
    python run_backtest.py <run_dir>
    
Example:
    python run_backtest.py runs/test-btc-backtest
"""

import sys
import os
import json

# Add site-packages to path
import site
site_packages = site.getsitepackages()[0]
sys.path.insert(0, site_packages)

from src.tools.backtest_tool import run_backtest

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_backtest.py <run_dir>")
        print("Example: python run_backtest.py runs/my-strategy")
        sys.exit(1)
    
    run_dir = sys.argv[1]
    
    # Make path absolute if relative
    if not os.path.isabs(run_dir):
        run_dir = os.path.abspath(run_dir)
    
    print(f"Running backtest for: {run_dir}")
    print("=" * 60)
    
    result = run_backtest(run_dir)
    result_json = json.loads(result)
    
    if result_json["status"] == "ok":
        metrics = json.loads(result_json["stdout"])
        print("\n📊 Backtest Results:")
        print(f"  Final Value:     ${metrics['final_value']:,.2f}")
        print(f"  Total Return:     {metrics['total_return']*100:.2f}%")
        print(f"  Annual Return:    {metrics['annual_return']*100:.2f}%")
        print(f"  Sharpe Ratio:    {metrics['sharpe']:.3f}")
        print(f"  Max Drawdown:     {metrics['max_drawdown']*100:.2f}%")
        print(f"  Win Rate:         {metrics['win_rate']*100:.1f}%")
        print(f"  Trade Count:      {metrics['trade_count']}")
        print(f"\n✅ Status: SUCCESS")
        
        if result_json["artifacts"]:
            print("\n📁 Artifacts:")
            for name, path in result_json["artifacts"].items():
                print(f"  - {name}: {path}")
    else:
        print(f"\n❌ Status: FAILED")
        print(f"Error: {result_json.get('error', 'Unknown error')}")
        if result_json.get("stderr"):
            print(f"Stderr: {result_json['stderr']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
