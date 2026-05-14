# Production Deployment Guide

**Vibe-Crypto-Trading System - Production Deployment**

---

## Overview

This guide covers deploying the Vibe-Crypto-Trading system in a production environment with paper trading on Bybit testnet and OKX testnet.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Vibe-Crypto-Trading System                       │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend: Streamlit Dashboard (Port 8501)                          │
│  Backend: Trading Engine + Execution Layer                          │
│  Data: OKX (primary), Bybit (secondary)                             │
│  Risk: Live Risk Guard (pre-trade + post-trade)                     │
│  Notifications: Telegram + Console                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Telegram Bot Token (optional)
- API Keys for exchanges (testnet/demo)

## Environment Variables

Create `.env` file:

```bash
# LLM Provider (OpenRouter)
OPENROUTER_API_KEY=sk-or-v1-xxx

# Exchange API Keys (Testnet)
BYBIT_API_KEY=testnet_key
BYBIT_API_SECRET=testnet_secret
OKX_API_KEY=testnet_key
OKX_API_SECRET=testnet_secret
OKX_PASSPHRASE=testnet_passphrase

# Trading Configuration
INITIAL_CASH=100000
MAX_POSITION_SIZE=0.1
MAX_LEVERAGE=5

# Risk Settings
MAX_DRAWDOWN_DAILY=0.02
MAX_DRAWDOWN_WEEKLY=0.05
MAX_DRAWDOWN_MONTHLY=0.10

# Notification
TELEGRAM_BOT_TOKEN=bot_token
TELEGRAM_CHAT_ID=chat_id

# Dashboard
STREAMLIT_PORT=8501
```

## Docker Deployment

### docker-compose.yml

```yaml
version: '3.8'

services:
  vct-trading:
    build: .
    container_name: vct-trading
    environment:
      - PYTHONUNBUFFERED=1
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./runs:/app/runs
    restart: unless-stopped

  vct-dashboard:
    build: ./dashboard
    container_name: vct-dashboard
    ports:
      - "8501:8501"
    environment:
      - PYTHONUNBUFFERED=1
    env_file:
      - .env
    depends_on:
      - vct-trading
    restart: unless-stopped

networks:
  default:
    name: vct-network
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p data runs

# Run trading engine
CMD ["python", "-m", "execution.trading_engine"]
```

## Local Deployment

### 1. Install Dependencies

```bash
cd vct-project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run Tests

```bash
# Run all tests with coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run specific test suites
pytest tests/ -m unit
pytest tests/ -m e2e
pytest tests/ -m integration
```

### 4. Start Trading Engine

```bash
python -m execution.trading_engine
```

### 5. Start Dashboard

```bash
streamlit run dashboard/app.py
```

## Monitoring

### Health Checks

```bash
# Check if trading engine is running
curl http://localhost:8000/health

# Check dashboard
curl http://localhost:8501
```

### Logs

```bash
# View trading logs
tail -f runs/logs/trading.log

# View all logs
docker logs -f vct-trading
```

### Metrics

The system tracks:
- Signal processing rate
- Order fill rate
- PnL (daily/weekly/monthly)
- Risk metrics (VaR, exposure, drawdown)
- Trade count and win rate

## Trading Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Signal Generation (from iteration loop or manual)                │
│    └── Strategy generates trading signal                            │
├─────────────────────────────────────────────────────────────────────┤
│ 2. Risk Validation (live_risk_guard.py)                             │
│    └── Pre-trade checks: position size, exposure, VaR, leverage    │
│    └── If failed → signal rejected, logged                         │
├─────────────────────────────────────────────────────────────────────┤
│ 3. Signal Queue (signal_queue.py)                                    │
│    └── Priority-based queue with timeout                           │
│    └── Processed by trading engine                                 │
├─────────────────────────────────────────────────────────────────────┤
│ 4. Order Routing (trading_engine.py)                                │
│    └── Route to correct exchange (Bybit/OKX)                        │
│    └── Submit order via adapter                                    │
├─────────────────────────────────────────────────────────────────────┤
│ 5. Fill Handling                                                     │
│    └── Process fill confirmation                                   │
│    └── Update positions                                             │
│    └── Calculate PnL                                                │
├─────────────────────────────────────────────────────────────────────┤
│ 6. Post-Trade Risk Monitoring                                       │
│    └── Real-time PnL tracking                                      │
│    └── Drawdown monitoring                                          │
│    └── Circuit breaker checks                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Circuit Breakers

The system automatically halts trading when:

| Trigger | Threshold | Action |
|---------|------------|--------|
| Daily Drawdown | -2% | Halt until reset |
| Weekly Drawdown | -5% | Halt until reset |
| Monthly Drawdown | -10% | Halt until reset |
| VaR Breach | 99% VaR exceeded | Halt until reset |
| Max Leverage | >5x | Reject order |
| Consecutive Losses | 3+ | Warning + review |

## Rollback Procedures

### 1. Stop Trading

```bash
# Send SIGTERM to trading engine
docker stop vct-trading

# Or via API
curl -X POST http://localhost:8000/shutdown
```

### 2. Preserve State

```bash
# Backup current state
cp -r runs/backup/$(date +%Y%m%d_%H%M%S)/
```

### 3. Reset Circuit Breakers

```python
from execution.risk.live_risk_guard import LiveRiskGuard

guard = LiveRiskGuard()
guard.reset_circuit_breaker()
```

### 4. Restart

```bash
docker restart vct-trading
```

## Testing

### E2E Test Suite

```bash
# Run full E2E test suite
pytest tests/e2e/ -v

# Run specific E2E test
pytest tests/e2e/test_trading_engine.py -v

# Run with coverage
pytest tests/e2e/ --cov=execution --cov-report=html
```

### Integration Tests

```bash
# Test exchange connections
pytest tests/ -m integration -v

# Test with live exchanges (requires real API keys)
pytest tests/ -m live -v
```

## Security

- **API Keys**: Store in `.env` (gitignored)
- **Network**: Use VPN in production
- **Monitoring**: Enable log aggregation
- **Updates**: Keep dependencies updated

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | Service not running | Check docker ps |
| API error | Invalid API key | Verify .env |
| High latency | Network issue | Check VPN |
| Circuit breaker triggered | Risk limit exceeded | Check logs, reset |

### Debug Mode

```bash
export VCT_DEBUG=1
python -m execution.trading_engine --debug
```

## Production Checklist

- [ ] All tests passing (unit + E2E)
- [ ] Code coverage > 80%
- [ ] API keys configured
- [ ] Telegram notifications working
- [ ] Dashboard accessible
- [ ] Circuit breakers configured
- [ ] Monitoring enabled
- [ ] Backup procedure tested
- [ ] Rollback procedure documented

---

**Last Updated:** 2026-05-14