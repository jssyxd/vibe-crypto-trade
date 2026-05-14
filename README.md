# Vibe-Crypto-Trading

AI-powered crypto quantitative trading system using Vibe-Trading as the core framework.

## Overview

This project converts natural language trading strategy ideas into backtested, AI-iterated, auto-executed strategies on Bybit/OKX simulation accounts.

## Features

- **Natural Language → Strategy**: Describe trading ideas in plain English, AI generates Python code
- **Multi-Backtest Engines**: OKX data, Monte Carlo validation, Walk-Forward analysis
- **AI Auto-Iteration**: Automated parameter optimization (5 rounds max)
- **Risk Controls**: Position limits, leverage caps, drawdown circuit breakers
- **Pine Script Export**: One-click export to TradingView, MT5

## Quick Start

```bash
# Clone repository
git clone https://github.com/jssyxd/vibe-crypto-trade.git
cd vibe-crypto-trade

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Vibe-Trading
pip install vibe-trading-ai

# Configure API key
cp .env.example .env
nano .env  # Set LANGCHAIN_PROVIDER and API key

# Run first backtest
vibe-trading run -p "Backtest BTC-USDT with 20/50 MA crossover, last 90 days"
```

## Architecture

```
User (Natural Language) → Vibe-Trading Agent → Backtest Engine → AI Iteration Loop
                                    ↓
                            Execution Layer → Bybit Simnet / OKX Demo
                                    ↓
                            Risk Controller (Position/Leverage/Drawdown)
```

## Documentation

- [System Design](docs/superpowers/specs/2026-05-13-vibe-crypto-trading-design.md)
- [Phase 1 Plan](docs/superpowers/plans/2026-05-13-phase1-mvp-plan.md)
- [Kraken Design System](docs/kraken/DESIGN.md)
- [Development Log](DEVELOPMENT_LOG.md)

## Tech Stack

- Vibe-Trading (core framework)
- Python 3.11+
- FastAPI + React 19
- OKX/CCXT data sources
- Kraken UI design system

## License

MIT
