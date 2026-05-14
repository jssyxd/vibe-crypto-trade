# Quick Start: Vibe-Crypto-Trading

## Prerequisites

- Python 3.11+
- LLM API key (OpenRouter recommended for best compatibility)

## Setup (5 minutes)

```bash
# 1. Navigate to project
cd vibe-crypto-trade

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Vibe-Trading
pip install vibe-trading-ai

# 4. Configure environment
cp .env.example .env
# Edit .env and set:
# LANGCHAIN_PROVIDER=openrouter
# OPENROUTER_API_KEY=your_key_here
# OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
```

## Running Backtests

### Basic Backtest
```bash
vibe-trading run -p "Backtest BTC-USDT with 20/50 MA crossover, last 90 days"
```

### RSI Mean Reversion (Known Working Prompt)
```bash
vibe-trading run -p "Backtest RSI(14) mean reversion on BTC-USDT, last 90 days"
```

### MA Crossover Strategy
```bash
vibe-trading run -p "Backtest 20/50 MA crossover on BTC-USDT, last 90 days"
```

## Common Tasks

### List recent runs
```bash
vibe-trading --list
```

### Export to TradingView
```bash
vibe-trading --pine <run_id>
```

### Run a swarm team
```bash
vibe-trading --swarm-run quant_strategy_desk '{"universe": "BTC-USDT"}'
```

## Design Reference

See `docs/kraken/DESIGN.md` for Kraken-style UI guidelines.

## Known Issues & Workarounds

### Chinese Characters in Paths
- Avoid using paths with Chinese characters
- Use English-only paths for the project directory

### config.json Setup
- Ensure config.json is properly configured for backtest execution
- Check OKX API credentials if data loading fails

### OpenRouter Model Naming
- Use full model name: `meta-llama/llama-3.1-8b-instruct`
- Do not use shortened aliases

## Troubleshooting

- **LLM errors**: Check `.env` has valid API key and correct provider
- **Data errors**: OKX API may be rate-limited, try again later
- **Import errors**: Run `pip install -U vibe-trading-ai`
- **Path errors**: Ensure project path contains no Chinese characters