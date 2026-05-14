import vectorbt as vbt
import numpy as np
from datetime import datetime, timedelta
import ccxt

# Get BTC data from OKX using ccxt
end_date = datetime.now()
start_date = end_date - timedelta(days=90)

print("Fetching BTC/USDT data from OKX...")

# Initialize OKX exchange
exchange = ccxt.okx()

# Fetch OHLCV data
ohlcv = exchange.fetch_ohlcv("BTC/USDT", "1d", int(start_date.timestamp() * 1000), limit=90)

print(f"Loaded {len(ohlcv)} candles")

# Convert to pandas DataFrame
import pandas as pd
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# Create vectorbt data
data = vbt.Data.from_data(df)

# Calculate Moving Averages
fast_ma = vbt.MA.run(data.close, 20)
slow_ma = vbt.MA.run(data.close, 50)

# Generate signals
entries = fast_ma.ma_crossed_above(slow_ma)
exits = fast_ma.ma_crossed_below(slow_ma)

# Run backtest
print("\nRunning backtest...")
portfolio = vbt.Portfolio.from_signals(
    data.close,
    entries=entries,
    exits=exits,
    size=100,  # Fixed size
    fees=0.001
)

# Get metrics
sharpe = portfolio.sharpe_ratio()
win_rate = portfolio.win_rate()
max_drawdown = portfolio.max_drawdown()

print(f"\n=== Backtest Results ===")
print(f"Sharpe Ratio: {sharpe:.2f}")
print(f"Win Rate: {win_rate:.1%}")
print(f"Max Drawdown: {max_drawdown:.1%}")
print(f"Total Return: {portfolio.total_return():.1%}")

# Save results
results = {
    "strategy": "MA Crossover 20/50",
    "sharpe_ratio": float(sharpe),
    "win_rate": float(win_rate),
    "max_drawdown": float(max_drawdown),
    "total_return": float(portfolio.total_return()),
    "num_trades": int(portfolio.trades.count())
}

import json
with open("backtest_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to backtest_results.json")