# Vibe-Trading Swarm Presets

This document lists the swarm presets available in Vibe-Trading and documents the most useful ones for crypto trading.

## All Available Presets

| Preset | Agents | Purpose |
|--------|--------|---------|
| `technical_analysis_panel` | 6 | Classic TA + Ichimoku + harmonic patterns |
| `crypto_trading_desk` | 4 | Execution/crypto desk: funding/risk analysis |
| `crypto_research_lab` | 4 | On-chain data + DeFi protocol + market structure |
| `quant_strategy_desk` | 4 | Stock screening + factor research in parallel |
| `risk_committee` | 4 | Drawdown, tail risk, and market regime review |
| `investment_committee` | 4 | Long/short debate, risk review, PM final decision |
| `ml_quant_lab` | 3 | Feature engineering and model design |
| `pairs_research_lab` | 4 | Correlation scan and cointegration testing |
| `sentiment_intelligence_team` | 4 | News intel / social sentiment / capital flows |
| `global_allocation_committee` | 4 | A-shares + crypto + HK/US analysis |

---

## Crypto Trading Desk

**Preset:** `crypto_trading_desk`
**Agents:** 4
**Variables:** `target`, `timeframe`

### Purpose
Execution-focused crypto trading desk that handles funding rates, liquidity analysis, and risk assessment for crypto assets.

### When to Use
- Evaluating entry/exit points for crypto positions
- Analyzing funding rate opportunities (perp vs spot)
- Risk assessment for leveraged crypto positions
- Cross-exchange arbitrage analysis

### How to Run
```bash
vibe-trading --swarm-run crypto_trading_desk '{"target": "BTC-USDT", "timeframe": "1h"}'
```

---

## Quant Strategy Desk

**Preset:** `quant_strategy_desk`
**Agents:** 4
**Variables:** `market`, `goal`

### Purpose
Quantitative strategy development with parallel factor research and stock/crypto screening.

### When to Use
- Building systematic trading strategies
- Factor research and validation
- Screening for quantitative opportunities
- Strategy backtesting framework design

### How to Run
```bash
vibe-trading --swarm-run quant_strategy_desk '{"market": "crypto", "goal": "momentum"}'
```

---

## Technical Analysis Panel

**Preset:** `technical_analysis_panel`
**Agents:** 6
**Variables:** `target`, `timeframe`

### Purpose
Comprehensive technical analysis using multiple methodologies:
- Classic technical analysis (support/resistance, trendlines)
- Ichimoku cloud analysis
- Harmonic pattern recognition

### When to Use
- Multi-timeframe technical analysis for entry/exit signals
- Confirming trade setups with multiple TA methods
- Identifying chart patterns and price levels

### How to Run
```bash
vibe-trading --swarm-run technical_analysis_panel '{"target": "BTC-USDT", "timeframe": "4h"}'
```

---

## Risk Committee

**Preset:** `risk_committee`
**Agents:** 4
**Variables:** `goal`

### Purpose
Comprehensive risk review covering:
- Drawdown analysis
- Tail risk assessment
- Market regime detection

### When to Use
- Pre-trade risk approval
- Portfolio risk review
- Market volatility assessment
- Risk limit determination

### How to Run
```bash
vibe-trading --swarm-run risk_committee '{"goal": "evaluate_btc_position"}'
```

---

## Investment Committee

**Preset:** `investment_committee`
**Agents:** 4
**Variables:** `target`, `market`

### Purpose
Multi-agent investment decision process:
- Long/short thesis debate
- Risk review
- PM final decision

### When to Use
- Major investment decisions
- New position approval
- Portfolio rebalancing decisions
- Strategy implementation review

### How to Run
```bash
vibe-trading --swarm-run investment_committee '{"target": "ETH-USDT", "market": "crypto"}'
```

---

## Crypto Research Lab

**Preset:** `crypto_research_lab`
**Agents:** 4
**Variables:** `target`, `timeframe`

### Purpose
Deep crypto research combining:
- On-chain data analysis
- DeFi protocol analysis
- Market structure analysis

### When to Use
- Fundamental crypto research
- DeFi protocol evaluation
- On-chain metrics analysis
- Market structure assessment

### How to Run
```bash
vibe-trading --swarm-run crypto_research_lab '{"target": "SOL-USDT", "timeframe": "1d"}'
```

---

## Sentiment Intelligence Team

**Preset:** `sentiment_intelligence_team`
**Agents:** 4
**Variables:** `market`, `timeframe`

### Purpose
Market sentiment analysis:
- News intelligence
- Social media sentiment (Twitter, Telegram, Reddit)
- Capital flow analysis

### When to Use
- Sentiment-based entry/exit timing
- Social alpha detection
- News-driven trading decisions
- Crowd sentiment contrarian signals

### How to Run
```bash
vibe-trading --swarm-run sentiment_intelligence_team '{"market": "crypto", "timeframe": "4h"}'
```

---

## Pairs Research Lab

**Preset:** `pairs_research_lab`
**Agents:** 4
**Variables:** `market`, `sector`

### Purpose
Statistical pairs trading research:
- Correlation scanning
- Cointegration testing
- Pairs selection for mean-reversion strategies

### When to Use
- Finding trading pair opportunities
- Crypto pairs trading strategy development
- Cross-exchange arbitrage pairs
- Mean-reversion strategy setup

### How to Run
```bash
vibe-trading --swarm-run pairs_research_lab '{"market": "crypto", "sector": "layer1"}'
```

---

## Global Allocation Committee

**Preset:** `global_allocation_committee`
**Agents:** 4
**Variables:** `goal`, `risk_tolerance`

### Purpose
Cross-asset allocation analysis:
- A-shares analysis
- Crypto allocation
- HK/US markets analysis

### When to Use
- Multi-asset portfolio allocation
- Risk budget distribution
- Cross-market opportunity assessment
- Regional diversification analysis

### How to Run
```bash
vibe-trading --swarm-run global_allocation_committee '{"goal": "balanced_portfolio", "risk_tolerance": "moderate"}'
```

---

## ML Quant Lab

**Preset:** `ml_quant_lab`
**Agents:** 3
**Variables:** `market`, `target_value`, `goal`

### Purpose
Machine learning quantitative research:
- Feature engineering
- Model design
- Backtesting framework

### When to Use
- Building ML-powered trading systems
- Feature selection for predictive models
- Strategy automation development
- Pattern recognition systems

### How to Run
```bash
vibe-trading --swarm-run ml_quant_lab '{"market": "crypto", "target_value": "returns", "goal": "prediction"}'
```