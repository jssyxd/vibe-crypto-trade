"""Test basic MA crossover backtest for crypto."""
import subprocess
import os
import sys

def run_ma_crossover_backtest():
    """Run a simple 20/50 MA crossover backtest on BTC/USDT."""
    print("=" * 60)
    print("Running MA Crossover Backtest - BTC/USDT")
    print("=" * 60)
    
    work_dir = "/home/da/桌面/新建文件夹 2/vct-project"
    
    # Use Vibe-Trading CLI for natural language → backtest
    cmd = [
        "vibe-trading", "run",
        "-p", "Backtest a 20/50 day moving average crossover on BTC-USDT, last 90 days. Show Sharpe ratio, win rate, and max drawdown."
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        cwd=work_dir,
        capture_output=True,
        text=True,
        env=os.environ
    )
    
    print("\n--- STDOUT ---")
    print(result.stdout)
    
    if result.stderr:
        print("\n--- STDERR ---")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
    return result.returncode == 0

if __name__ == "__main__":
    success = run_ma_crossover_backtest()
    sys.exit(0 if success else 1)
