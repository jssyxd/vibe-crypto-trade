# Vibe-Crypto-Trading

AI-powered crypto quantitative trading system using Vibe-Trading as the core framework.

## 概述 (Overview)

This project converts natural language trading strategy ideas into backtested, AI-iterated, auto-executed strategies on Bybit/OKX simulation accounts.

本项目将自然语言交易策略想法转换为在Bybit/OKX模拟账户上进行回测、AI迭代、自动执行的策略。

## 特性 (Features)

- **自然语言 → 策略 (Natural Language → Strategy)**: 用简单的英语描述交易想法，AI生成Python代码
- **多回测引擎 (Multi-Backtest Engines)**: OKX数据、蒙特卡洛验证、Walk-Forward分析
- **AI自动迭代 (AI Auto-Iteration)**: 自动参数优化（最多5轮）
- **风险控制 (Risk Controls)**: 仓位限制、杠杆上限、回撤熔断机制
- **Pine Script导出 (Pine Script Export)**: 一键导出到TradingView、MT5
- **实时监控 (Real-time Monitoring)**: Streamlit仪表板，泰勒消息通知

## 快速开始 (Quick Start)

```bash
# 克隆仓库 (Clone repository)
git clone https://github.com/jssyxd/vibe-crypto-trade.git
cd vibe-crypto-trade

# 创建虚拟环境 (Create virtual environment)
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖 (Install dependencies)
pip install -r requirements.txt

# 配置API密钥 (Configure API key)
cp .env.example .env
nano .env  # 设置 LLM API密钥

# 运行回测 (Run backtest)
python -c "from iteration.iteration_loop import IterationLoop; print('Test import OK')"

# 启动仪表板 (Start dashboard)
streamlit run dashboard/app.py
```

## 系统架构 (Architecture)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Vibe-Crypto-Trading System                         │
├─────────────────────────────────────────────────────────────────────────┤
│  Phase 1: AI Strategy Generation (Natural Language → Code)              │
│           Templates: MA Cross, RSI, Bollinger, Momentum                │
├─────────────────────────────────────────────────────────────────────────┤
│  Phase 2: Execution Layer (Bybit Simnet + OKX Demo)                    │
│           Adapters: Base → Bybit/OKX, Signal Queue, Risk Controller     │
├─────────────────────────────────────────────────────────────────────────┤
│  Phase 3: AI Auto-Iteration (5-round Bayesian optimization)            │
│           Strategy Generator → Metrics Evaluator → Parameter Optimizer │
├─────────────────────────────────────────────────────────────────────────┤
│  Phase 4: Monitoring & Portfolio                                       │
│           Portfolio Manager, Advanced Risk (VaR), Dashboard, Alerts    │
├─────────────────────────────────────────────────────────────────────────┤
│  Phase 5: Live Trading Integration                                     │
│           Test Infrastructure, Paper Trading, Live Risk, E2E Engine   │
└─────────────────────────────────────────────────────────────────────────┘

UI: Kraken-styled Streamlit Dashboard (Port 8501)
Notifications: Telegram + Console
Risk: VaR + Exposure + Drawdown Circuit Breakers
Testing: Unit (321+) + E2E + Integration
Deployment: Docker + docker-compose
```

## 目录结构 (Directory Structure)

```
vct-project/
├── execution/                 # Execution layer
│   ├── adapters/            # Exchange adapters (Bybit, OKX)
│   ├── risk/                # Risk controllers
│   ├── signals/             # Signal queue
│   ├── core/                # Execution engine
│   └── trading_engine.py    # E2E trading orchestrator
├── iteration/               # AI auto-iteration
│   ├── strategy_generator.py
│   ├── metrics_evaluator.py
│   ├── parameter_optimizer.py
│   └── iteration_loop.py
├── portfolio/               # Portfolio management
├── dashboard/              # Streamlit dashboard
├── notifications/          # Telegram + Console notifications
├── tests/                  # Test suite
│   ├── conftest.py         # Test fixtures
│   ├── e2e/                # E2E tests
│   └── test_*.py           # Unit tests
├── docs/                   # Documentation
│   ├── kraken/             # UI design system
│   └── superpowers/        # Specs and plans
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── PRODUCTION.md           # Deployment guide
├── QUICKSTART.md          # Quick start guide
└── DEVELOPMENT_LOG.md     # Development log
```

## 测试 (Testing)

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=execution --cov-report=term-missing

# Run specific test suite
pytest tests/ -m unit      # Unit tests only
pytest tests/ -m e2e        # E2E tests only
pytest tests/ -m integration  # Integration tests

# Run specific test file
pytest tests/test_trading_engine.py -v
```

**Test Results:**
- 321 passed, 6 skipped
- Overall coverage: 75%
- Core modules: 84-94% coverage

## 部署 (Deployment)

### Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker logs -f vct-trading

# Stop
docker-compose down
```

### 本地部署 (Local Deployment)

```bash
# Trading engine
python -m execution.trading_engine

# Dashboard (separate terminal)
streamlit run dashboard/app.py --port 8501
```

## 开发日志 (Development Log)

详细的开发过程、调试记录、思考思路见 [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)

### 关键里程碑 (Key Milestones)

| 日期 | 阶段 | 状态 |
|------|------|------|
| 2026-05-13 | Phase 1: AI Strategy Generation | ✅ |
| 2026-05-14 | Phase 2: Execution Layer | ✅ |
| 2026-05-14 | Phase 3: AI Auto-Iteration | ✅ |
| 2026-05-14 | Phase 4: Monitoring & Portfolio | ✅ |
| 2026-05-15 | Phase 5: Live Trading Integration | ✅ |

### 调试记录 (Debug Notes)

1. **LLM Provider切换**: DeepSeek API无效 → 切换到OpenRouter (Llama 3.1 8B)
2. **config.json路径问题**: 中文路径导致CLI失败 → 使用Python API直接调用
3. **LIMIT订单状态**: LIMIT订单错误设置为FILLED → 修改为PENDING状态
4. **E2E测试期望**: 多个测试期望值与实现不一致 → 修正测试期望

## 文档 (Documentation)

- [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) - 完整的开发日志
- [PRODUCTION.md](PRODUCTION.md) - 生产部署指南
- [QUICKSTART.md](QUICKSTART.md) - 快速开始指南
- [System Design](docs/superpowers/specs/2026-05-13-vibe-crypto-trading-design.md)
- [Kraken Design System](docs/kraken/DESIGN.md)

## 技术栈 (Tech Stack)

- Vibe-Trading (核心框架)
- Python 3.11+
- CCXT (交易所连接)
- Streamlit + Plotly (仪表板)
- pytest (测试)
- Docker (部署)

## 许可证 (License)

MIT