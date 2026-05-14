# Baseline Workflow: Natural Language → Backtest

## Overview
This document establishes the baseline workflow for using Vibe-Trading
to convert natural language strategy ideas into backtested results.

## Workflow Steps

### 1. Strategy Description
User describes strategy in natural language:
```
"When BTC is above its 200-day moving average and RSI(14) drops below 30,
buy with 5% of portfolio. Exit when RSI exceeds 70."
```

### 2. Vibe-Trading Processing
Vibe-Trading agent:
1. Parses natural language → Python strategy code
2. Loads BTC/USDT data from OKX
3. Runs backtest with specified parameters
4. Calculates metrics

### 3. Backtest Results
Output metrics:
- **Sharpe Ratio**: Risk-adjusted return (target: > 1.5)
- **Win Rate**: Percentage of profitable trades (target: > 55%)
- **Max Drawdown**: Largest peak-to-trough decline (target: < 20%)
- **Total Trades**: Number of trades executed
- **Profit Factor**: Gross profit / gross loss (target: > 1.5)

### 4. Interpretation
- If metrics meet thresholds → strategy is viable for paper trading
- If metrics don't meet thresholds → AI can iterate with parameter adjustments
- If still failing after 5 iterations → discard strategy, try new approach

## Example Commands

### Basic Backtest
```bash
vibe-trading run -p "Backtest RSI(14) mean reversion on BTC-USDT, last 90 days"
```

### With Swarm
```bash
vibe-trading --swarm-run quant_strategy_desk '{"universe": "BTC-USDT", "horizon": "90 days"}'
```

### Export to TradingView
```bash
vibe-trading --pine <run_id>
```

## Environment Setup
1. Copy `.env.example` to `.env`
2. Set LLM provider (OpenRouter recommended)
3. Run `vibe-trading run -p "test"` to verify setup

## Known Issues
- Chinese characters in paths may cause issues
- config.json setup needed for backtest
- OpenRouter model naming: use `meta-llama/llama-3.1-8b-instruct`