# Vibe-Crypto-Trading System Design

**Date:** 2026-05-13
**Status:** Draft v1.0
**Author:** AI Agent (Brainstorming with User)

---

## 1. Overview

### Project Name
`vibe-crypto-trade`

### Mission
A Vibe-Trading-based crypto quantitative trading system that converts natural language strategy ideas into backtested, AI-iterated, auto-executed trading strategies on Bybit/OKX simulation accounts.

### Principles
- **Vibe-coding first**: Explore and iterate quickly with AI tools
- **Progressive complexity**: MVP → Extended → Production
- **Security boundary**: Simulation only, no real funds
- **AI-driven iteration**: Fully automated generation → backtest → evaluation → optimization loop

---

## 2. User Requirements Summary

| Requirement | Choice |
|-------------|--------|
| Core framework | Vibe-Trading (Option A) |
| Strategy input | Natural language (Option A) |
| AI iteration | Fully automated (Option A) |
| Execution | Backtest + Simulation auto-execution (Option C) |
| Risk control | All three (position/leverage/drawdown) + AI adaptive (Option D) |
| Architecture | Progressive evolution (Option C) |

---

## 3. Architecture

### 3.1 Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                        User                                  │
│              "When BTC above 200MA and RSI < 30, buy"        │
└──────────────────────────┬──────────────────────────────────┘
                           │ Natural Language
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Vibe-Trading (Core)                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Agent: ReAct Loop + 5-layer context compression       ││
│  │  Swarm: crypto_trading_desk (strategy → backtest →    ││
│  │         risk audit)                                    ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  74 Finance Skills                                      ││
│  │  - strategy-generate, cross-market-strategy            ││
│  │  - backtest-diagnose, pine-script                      ││
│  │  - technical-basic, ml-strategy                        ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  7 Backtest Engines (built-in)                         ││
│  │  - CryptoEngine (OKX/CCXT data)                        ││
│  │  - CompositeEngine (cross-market)                      ││
│  │  - statistical validation: Monte Carlo, Walk-Forward   ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Memory: Cross-session persistent, FTS5 search         ││
│  │  Skills: Self-evolving, full CRUD                      ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Data Sources (built-in)                               ││
│  │  - OKX loader (crypto)                                ││
│  │  - CCXT (100+ exchanges)                              ││
│  │  - YFinance (HK/US)                                   ││
│  │  - AKShare (China A-share)                            ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────┘
                           │ Strategy validated
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Execution Layer (New - Phase 2)                 │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────┐ │
│  │ Bybit Adapter │  │ OKX Adapter   │  │ Signal Queue    │ │
│  │ (Simnet)      │  │ (Demo)        │  │ (Redis/Queue)   │ │
│  └───────────────┘  └───────────────┘  └─────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Risk Controller                                        ││
│  │  - Position limits (per trade, per symbol, total)     ││
│  │  - Leverage limits (max leverage, auto-adjust)         ││
│  │  - Drawdown circuit breaker (daily/weekly/monthly)    ││
│  │  - AI Volatility Adapter (dynamic risk adjustment)    ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────┬──────────────────────────────────┘
                           │ Validated order
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Exchange (Simulation)                      │
│          Bybit Simnet + OKX Demo Trading                   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
1. User Input
   "When BTC breaks above 200-day MA and RSI < 30, buy with 5% position"

2. Vibe-Trading Agent (Swarm: crypto_trading_desk)
   ├── Strategy Generator → Python strategy code
   ├── Backtest Engine → Historical validation
   │   ├── OKX data (2023-2026)
   │   ├── Multiple timeframes (1h, 4h, 1d)
   │   ├── Monte Carlo validation
   │   └── Walk-Forward analysis
   └── Risk Auditor → Evaluate Sharpe/MaxDrawdown/WinRate

3. AI Iteration Loop (Auto)
   ├── IF metrics < threshold:
   │   ├── Adjust parameters (RSI period, MA length)
   │   ├── Modify entry conditions
   │   └── Re-backtest
   └── REPEAT until达标 OR max_iterations

4. Execution Layer
   ├── Risk Controller checks:
   │   ├── Position size ✓
   │   ├── Leverage ✓
   │   ├── Drawdown circuit ✓
   │   └── AI volatility adjustment ✓
   └── Order to Exchange (Simnet/Demo)

5. Monitor & Memory
   ├── Record all trades
   ├── Update agent memory
   └── Continuous learning
```

---

## 4. Phases

### Phase 1: MVP (Week 1-2)
**Goal:** Get Vibe-Trading running with crypto backtest

| Task | Description |
|------|-------------|
| P1.1 | Install Vibe-Trading (`pip install vibe-trading-ai`) |
| P1.2 | Configure LLM (DeepSeek/OpenAI) in `agent/.env` |
| P1.3 | Test OKX data source for BTC/USDT |
| P1.4 | Run first crypto backtest (e.g., MA crossover) |
| P1.5 | Verify backtest metrics (Sharpe, WinRate, MaxDrawdown) |
| P1.6 | Test Pine Script export (`/pine` command) |
| P1.7 | Explore 29 swarm presets, identify useful ones |
| P1.8 | Document workflow, establish baseline |

**Exit Criteria:**
- Can run natural language → backtest for BTC
- Metrics displayed: Sharpe ratio, win rate, max drawdown
- Pine Script export works

---

### Phase 2: Execution Layer (Week 3-4)
**Goal:** Connect to Bybit/OKX simulation accounts

| Task | Description |
|------|-------------|
| P2.1 | Develop Bybit Adapter (Simnet) |
| P2.2 | Develop OKX Adapter (Demo) |
| P2.3 | Implement Signal Queue (Redis or in-memory) |
| P2.4 | Implement Risk Controller (position/leverage/drawdown) |
| P2.5 | Implement AI Volatility Adapter |
| P2.6 | End-to-end test: strategy → backtest → paper trade |
| P2.7 | Verify order execution on sim accounts |

**Exit Criteria:**
- Strategy validated by backtest → auto-executes on Bybit Simnet
- Risk controls prevent oversized positions
- Drawdown circuit breaker works

---

### Phase 3: AI Auto-Iteration (Week 5-6)
**Goal:** Implement automated strategy optimization loop

| Task | Description |
|------|-------------|
| P3.1 | Define iteration loop in agent workflow |
| P3.2 | Configure metrics threshold (e.g., Sharpe > 1.5) |
| P3.3 | Implement parameter adjustment logic |
| P3.4 | Add max iteration limits (prevent infinite loops) |
| P3.5 | Test: "Generate a BTC RSI mean-reversion strategy, iterate until Sharpe > 1.5" |
| P3.6 | Monitor iteration quality, adjust prompt |

**Exit Criteria:**
- AI generates strategy → backtests → if fails, auto-adjusts → retries
- 5 iterations max, then stop and report
- Final strategy saved to memory

---

### Phase 4: Extended Features (Week 7+)
**Goal:** Multi-strategy, multi-exchange, advanced features

| Task | Description |
|------|-------------|
| P4.1 | Multi-strategy parallel execution |
| P4.2 | Add Bybit live data connection |
| P4.3 | Advanced risk controls (portfolio-level) |
| P4.4 | crypto-kol-quant factor integration |
| P4.5 | Advanced visualizations (Dune/streamlit dashboards) |
| P4.6 | Notification system (Telegram/Slack on trade) |

---

## 5. Key Technical Decisions

### 5.1 Vibe-Trading Integration
- **Do NOT modify** Vibe-Trading source code
- Use as external service via API: `vibe-trading serve`
- Communicate via REST API + WebSocket for real-time
- Or use CLI: `vibe-trading run -p "..."`

### 5.2 Execution Layer Location
- New repository: `vibe-crypto-execution`
- Interfaces with Vibe-Trading via files (run directory) + API
- Keeps execution logic separate for security

### 5.3 Data Sources (Priority)
1. **OKX** (primary for crypto) - built into Vibe-Trading
2. **CCXT** (fallback) - 100+ exchanges
3. **YFinance** (for correlation analysis)

### 5.4 Export Targets
- **TradingView Pine Script v6** (via `/pine` command, built-in)
- **MT5 MQL5** (via built-in export)
- **vectorbt** (for Python-native backtesting)

---

## 6. Frontend Design

Use **Kraken DESIGN.md** as reference for UI styling.

### Key Pages (Future)

| Page | Description |
|------|-------------|
| Dashboard | Portfolio overview, PnL, open positions |
| Strategy Builder | Natural language input, strategy history |
| Backtest Results | Equity curve, metrics, trade log |
| Live Monitor | Real-time positions, signals, risk status |
| Settings | Exchange API keys (simulation only), risk parameters |

### Design Tokens (Kraken Style)
- Primary: `#7132f5` (Kraken Purple)
- Canvas: `#ffffff` (Light mode) / `#101114` (Dark surfaces)
- Card: `#ffffff` (Light) / `#1a1a1f` (Dark)
- Trading Up: `#149e61` (Green)
- Trading Down: `#f6465d` (Red)
- Font: Kraken-Brand (headings) + Kraken-Product (body)
- Border Radius: 12px max (no pills)

---

## 7. Security Considerations

| Rule | Implementation |
|------|----------------|
| No real funds | Simulation accounts only (Bybit Simnet, OKX Demo) |
| API keys | Never commit to git, use `.env` |
| Execution isolation | Execution layer runs separately from Vibe-Trading |
| Circuit breakers | Hard stops on drawdown thresholds |
| Audit trail | All trades logged to file + memory |

---

## 8. Dependencies

| Package | Purpose | Phase |
|---------|---------|-------|
| `vibe-trading-ai` | Core framework | P1 |
| `ccxt` | Exchange data | P1 |
| `vectorbt` | Advanced backtesting | P1 |
| `okx-sdk` | OKX trading API | P2 |
| `bybit-sdk` | Bybit trading API | P2 |
| `redis` | Signal queue | P2 |
| `pydantic` | Data validation | P2 |

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Backtest win rate | > 55% |
| Sharpe ratio | > 1.5 |
| Max drawdown | < 20% |
| Strategy iteration time | < 5 min per round |
| AI auto-iteration success rate | > 70% reach threshold |

---

## 10. Next Steps

1. **User approves this design**
2. Invoke `writing-plans` skill to create Phase 1 implementation plan
3. Start with: Install Vibe-Trading, test first crypto backtest

---

*This spec will be refined as we learn more through implementation.*