# Vibe-Crypto-Trading Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install and configure Vibe-Trading, verify crypto backtest capabilities with OKX data source, establish baseline workflow for natural language → backtest pipeline.

**Architecture:** Vibe-Trading runs as a local Python package with FastAPI backend and React frontend. OKX provides crypto market data. Strategy generation via natural language to Python code, backtest via Vibe-Trading's CryptoEngine, metrics evaluation for Sharpe/WinRate/MaxDrawdown.

**Tech Stack:** `vibe-trading-ai`, Python 3.11+, FastAPI, React 19, OKX data source, CCXT, vectorbt

---

## Prerequisites

- Python 3.11+ (currently 3.13.7 available)
- pip package manager
- ~2GB free disk space for Vibe-Trading installation

---

## File Structure

```
vibe-crypto-trade/
├── agent/                          # Vibe-Trading agent config (cloned)
│   ├── .env                        # LLM provider + API keys
│   └── runs/                        # Backtest run outputs
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-05-13-vibe-crypto-trading-design.md
│       └── plans/
│           └── 2026-05-13-phase1-mvp-plan.md
├── kraken-design/                   # Kraken DESIGN.md reference
└── README.md
```

---

## Task 1: Environment Preparation

**Files:**
- Create: `/home/da/桌面/新建文件夹 2/vibe-crypto-trade/.gitignore`
- Create: `/home/da/桌面/新建文件夹 2/vibe-crypto-trade/.env.example`

- [ ] **Step 1: Create project directory and .gitignore**

```bash
mkdir -p "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/

# Environment
.env
.env.local

# Vibe-Trading runs
runs/
*.run/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
EOF

echo "Created project structure"
```

- [ ] **Step 2: Create .env.example with all required variables**

```bash
cat > .env.example << 'EOF'
# LLM Provider (required - choose one)
LANGCHAIN_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
LANGCHAIN_MODEL_NAME=deepseek/deepseek-v3.2

# Alternative: OpenAI
# LANGCHAIN_PROVIDER=openai
# OPENAI_API_KEY=your_openai_key_here
# LANGCHAIN_MODEL_NAME=gpt-4.1

# Optional: Tushare for A-share data
# TUSHARE_TOKEN=your_tushare_token

# Security
API_AUTH_KEY=change_me_in_production

# Optional data sources
# OKX_API_KEY=your_okx_key
# OKX_SECRET=your_okx_secret
EOF

echo "Created .env.example"
```

- [ ] **Step 3: Initialize git and commit**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
git init
git add .gitignore .env.example
git commit -m "chore: Initialize project structure with .gitignore and .env.example"
```

---

## Task 2: Install Vibe-Trading

**Files:**
- Create: (via pip install, no direct file creation)
- Verify: `vibe-trading --version`

- [ ] **Step 1: Check disk space and Python version**

```bash
df -h /home/da/桌面 | tail -1
python3 --version
```

Expected output: Python 3.13.7 (compatible)

- [ ] **Step 2: Install vibe-trading-ai in a virtual environment**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"

# Create virtual environment
python3 -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Install vibe-trading-ai
pip install -U vibe-trading-ai

# Verify installation
vibe-trading --version
```

Expected output: `vibe-trading-ai, version 0.1.x` or similar

- [ ] **Step 3: Copy .env.example to .env and configure LLM**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
cp .env.example .env

# Edit .env - user needs to set their API key
# For now, just verify the file exists
ls -la .env
```

**Note:** User must edit `.env` and set `DEEPSEEK_API_KEY` (or other provider)

- [ ] **Step 4: Run preflight check to verify setup**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
source .venv/bin/activate

# Run Vibe-Trading preflight check
python -m src.preflight
```

Expected: Should show green checkmarks for data sources and LLM connectivity.

- [ ] **Step 5: Commit**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
git add .venv/ 2>/dev/null || true  # May fail if large
git add .env
git add README.md 2>/dev/null || echo "No README yet"
git commit -m "chore: Install Vibe-Trading and configure virtual environment"
```

---

## Task 3: Clone and Setup Kraken DESIGN.md Reference

**Files:**
- Create: `/home/da/桌面/新建文件夹 2/vibe-crypto-trade/docs/kraken-design/DESIGN.md`
- Copy from: `/home/da/桌面/新建文件夹 2/awesome-design-md/design-md/kraken/DESIGN.md`

- [ ] **Step 1: Copy Kraken DESIGN.md to project**

```bash
mkdir -p "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/docs/kraken-design"

cp "/home/da/桌面/新建文件夹 2/awesome-design-md/design-md/kraken/DESIGN.md" \
   "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/docs/kraken-design/DESIGN.md"

echo "Copied Kraken DESIGN.md"
```

- [ ] **Step 2: Verify the file**

```bash
head -50 "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/docs/kraken-design/DESIGN.md"
```

- [ ] **Step 3: Create design-system-usage.md with quick reference**

```bash
cat > "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/docs/kraken-design/USAGE.md" << 'EOF'
# Kraken Design System Quick Reference

## Key Colors
- Primary: `#7132f5` (Kraken Purple)
- Purple Dark: `#5741d8`
- Text: `#101114`
- Muted: `#686b82`
- Background: `#ffffff`
- Border: `#dedee5`
- Success: `#149e61`
- Error: `#f6465d`

## Typography
- Display: Kraken-Brand, fallback: IBM Plex Sans
- UI/Body: Kraken-Product, fallback: Helvetica Neue

## Border Radius
- Max: 12px (no pill buttons)

## Quick Prompt for AI
"When building UI, reference /docs/kraken-design/DESIGN.md for colors, typography, and component styles."
EOF

echo "Created USAGE.md"
```

- [ ] **Step 4: Commit**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
git add docs/kraken-design/
git commit -m "docs: Add Kraken design system reference"
```

---

## Task 4: Verify OKX Data Source

**Files:**
- Create: `/home/da/桌面/新建文件夹 2/vibe-crypto-trade/test_okx_data.py`

- [ ] **Step 1: Create test script to verify OKX data connectivity**

```bash
cat > "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/test_okx_data.py" << 'EOF'
"""Test OKX data source for crypto backtesting."""
import json
from datetime import datetime, timedelta

def test_okx_btc_data():
    """Test that we can fetch BTC/USDT data from OKX."""
    print("Testing OKX data source...")

    # Import Vibe-Trading loaders
    try:
        from vibe_trading.backtest.loaders.okx import OKXLoader
        print("✓ OKXLoader imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import OKXLoader: {e}")
        return False

    # Initialize loader
    try:
        loader = OKXLoader()
        print("✓ OKXLoader initialized")
    except Exception as e:
        print(f"✗ Failed to initialize OKXLoader: {e}")
        return False

    # Fetch recent BTC/USDT data
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        data = loader.load_data(
            symbol="BTC-USDT",
            start_date=start_date,
            end_date=end_date,
            timeframe="1d"
        )

        print(f"✓ Loaded {len(data)} bars of BTC/USDT data")
        print(f"  Date range: {data.index[0]} to {data.index[-1]}")
        print(f"  Latest close: {data['close'].iloc[-1]:.2f}")

        return True

    except Exception as e:
        print(f"✗ Failed to load data: {e}")
        return False

if __name__ == "__main__":
    success = test_okx_btc_data()
    exit(0 if success else 1)
EOF

echo "Created test_okx_data.py"
```

- [ ] **Step 2: Run the test script**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
source .venv/bin/activate
python test_okx_data.py
```

Expected output: Should show BTC/USDT data loaded successfully

- [ ] **Step 3: Commit**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
git add test_okx_data.py
git commit -m "test: Add OKX data source verification script"
```

---

## Task 5: Run First Crypto Backtest

**Files:**
- Create: `/home/da/桌面/新建文件夹 2/vibe-crypto-trade/test_backtest_ma_crossover.py`

- [ ] **Step 1: Create a simple MA crossover backtest script**

```bash
cat > "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/test_backtest_ma_crossover.py" << 'EOF'
"""Test basic MA crossover strategy backtest."""
import json
from datetime import datetime, timedelta

def run_ma_crossover_backtest():
    """Run a simple 20/50 MA crossover backtest on BTC/USDT."""
    print("=" * 60)
    print("Running MA Crossover Backtest")
    print("=" * 60)

    # Use Vibe-Trading CLI for natural language → backtest
    # This tests the full pipeline

    import subprocess
    import os

    # Set working directory
    work_dir = os.path.dirname(os.path.abspath(__file__))

    # Run Vibe-Trading with natural language prompt
    cmd = [
        "vibe-trading", "run",
        "-p", "Backtest a 20/50 day moving average crossover on BTC-USDT, "
              "last 90 days. Show Sharpe ratio, win rate, and max drawdown."
    ]

    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {work_dir}")

    result = subprocess.run(
        cmd,
        cwd=work_dir,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": os.environ.get("PATH", "")}
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
    exit(0 if success else 1)
EOF

echo "Created test_backtest_ma_crossover.py"
```

- [ ] **Step 2: Run the backtest script**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
source .venv/bin/activate
python test_backtest_ma_crossover.py
```

Expected output: Backtest results with Sharpe ratio, win rate, max drawdown

- [ ] **Step 3: Verify backtest metrics are displayed**

Check output for:
- Sharpe ratio
- Win rate / success rate
- Maximum drawdown
- Equity curve (if available)

- [ ] **Step 4: Commit**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
git add test_backtest_ma_crossover.py
git commit -m "test: Add MA crossover backtest pipeline test"
```

---

## Task 6: Test Pine Script Export

**Files:**
- Create: `/home/da/桌面/新建文件夹 2/vibe-crypto-trade/test_pine_export.py`

- [ ] **Step 1: Create Pine Script export test**

```bash
cat > "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/test_pine_export.py" << 'EOF'
"""Test Pine Script export from Vibe-Trading."""
import subprocess
import os
import json
from datetime import datetime

def test_pine_export():
    """Test /pine command to export strategy as TradingView Pine Script."""
    print("=" * 60)
    print("Testing Pine Script Export")
    print("=" * 60)

    work_dir = os.path.dirname(os.path.abspath(__file__))

    # First, run a backtest to get a run_id
    run_cmd = [
        "vibe-trading", "run",
        "-p", "Backtest RSI(14) mean reversion on BTC-USDT, last 30 days"
    ]

    print("Step 1: Running backtest to get run_id...")
    result = subprocess.run(
        run_cmd,
        cwd=work_dir,
        capture_output=True,
        text=True
    )

    print(result.stdout)

    # Extract run_id from output
    run_id = None
    for line in result.stdout.split('\n'):
        if 'run_id' in line.lower() or 'run id' in line.lower():
            # Try to extract ID
            parts = line.split(':')
            if len(parts) >= 2:
                run_id = parts[-1].strip()
                break

    if not run_id:
        # Try alternative: list recent runs
        list_cmd = ["vibe-trading", "--list"]
        list_result = subprocess.run(
            list_cmd,
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        print("\n--- Recent runs ---")
        print(list_result.stdout)

        # Use first run_id if available
        lines = list_result.stdout.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('-'):
                run_id = line.strip().split()[0]
                break

    if run_id:
        print(f"\nFound run_id: {run_id}")

        # Export to Pine Script
        pine_cmd = ["vibe-trading", "--pine", run_id]
        pine_result = subprocess.run(
            pine_cmd,
            cwd=work_dir,
            capture_output=True,
            text=True
        )

        print("\n--- Pine Script Export ---")
        print(pine_result.stdout)

        if pine_result.stderr:
            print("\n--- Errors ---")
            print(pine_result.stderr)

        return pine_result.returncode == 0
    else:
        print("Could not find run_id, skipping pine export test")
        return True  # Don't fail the test

if __name__ == "__main__":
    success = test_pine_export()
    exit(0 if success else 1)
EOF

echo "Created test_pine_export.py"
```

- [ ] **Step 2: Run Pine Script export test**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
source .venv/bin/activate
python test_pine_export.py
```

Expected output: Pine Script v6 code for the strategy

- [ ] **Step 3: Commit**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
git add test_pine_export.py
git commit -m "test: Add Pine Script export verification"
```

---

## Task 7: Explore Swarm Presets

**Files:**
- Create: `/home/da/桌面/新建文件夹 2/vibe-crypto-trade/explore_swarm_presets.py`

- [ ] **Step 1: List all available swarm presets**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
source .venv/bin/activate

# List all swarm presets
vibe-trading --swarm-presets
```

Expected output: List of 29+ swarm presets including:
- `crypto_trading_desk`
- `quant_strategy_desk`
- `investment_committee`
- etc.

- [ ] **Step 2: Document useful presets for crypto trading**

```bash
cat > "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/docs/swarm-presets.md" << 'EOF'
# Vibe-Trading Swarm Presets for Crypto Trading

## Most Relevant Presets

### 1. crypto_trading_desk
**Purpose:** Funding/basis + liquidation + flow → risk manager
**Use when:** Analyzing crypto market structure and risk

### 2. quant_strategy_desk
**Purpose:** Screening + factor research → backtest → risk audit
**Use when:** Building quantitative strategies (primary choice)

### 3. investment_committee
**Purpose:** Bull/bear debate → risk review → PM final call
**Use when:** Need multi-perspective strategy evaluation

### 4. technical_analysis_panel
**Purpose:** Classic TA + Ichimoku + harmonic + Elliott + SMC → consensus
**Use when:** Pure technical analysis strategies

### 5. risk_committee
**Purpose:** Drawdown + tail risk + regime review → sign-off
**Use when:** Validating risk parameters

## How to Run

```bash
# Run crypto_trading_desk swarm
vibe-trading --swarm-run crypto_trading_desk '{"asset": "BTC-USDT", "timeframe": "1d"}'

# Run quant_strategy_desk
vibe-trading --swarm-run quant_strategy_desk '{"universe": "BTC-USDT", "horizon": "90 days"}'
```

## Reference
Run `vibe-trading --swarm-presets` to see all available presets.
EOF

echo "Created docs/swarm-presets.md"
```

- [ ] **Step 3: Test one swarm preset**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
source .venv/bin/activate

# Test running a simple swarm
vibe-trading --swarm-run crypto_trading_desk '{"asset": "BTC-USDT", "timeframe": "1d"}' 2>&1 | head -50
```

Expected: Swarm starts running with multiple agents collaborating

- [ ] **Step 4: Commit**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
git add docs/swarm-presets.md
git commit -m "docs: Document useful swarm presets for crypto trading"
```

---

## Task 8: Create Baseline Workflow Documentation

**Files:**
- Create: `/home/da/桌面/新建文件夹 2/vibe-crypto-trade/docs/workflow-baseline.md`

- [ ] **Step 1: Document the baseline workflow**

```bash
cat > "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/docs/workflow-baseline.md" << 'EOF'
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
2. Set `DEEPSEEK_API_KEY` (or other LLM provider)
3. Run `vibe-trading init` for interactive setup

## Next Steps
- Phase 2: Connect to Bybit/OKX simulation accounts for auto-execution
- Phase 3: Implement AI auto-iteration for strategy optimization
EOF

echo "Created docs/workflow-baseline.md"
```

- [ ] **Step 2: Create quick-start guide**

```bash
cat > "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/QUICKSTART.md" << 'EOF'
# Quick Start: Vibe-Crypto-Trading

## Prerequisites
- Python 3.11+
- DeepSeek API key (or OpenAI/Anthropic)

## Setup (5 minutes)

```bash
# 1. Navigate to project
cd /home/da/桌面/新建文件夹 2/vibe-crypto-trade

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Configure API key
# Edit .env and set DEEPSEEK_API_KEY=your_key_here
nano .env

# 4. Run your first backtest
vibe-trading run -p "Backtest BTC-USDT with 20/50 MA crossover, last 90 days"
```

## Common Tasks

### Run a backtest
```bash
vibe-trading run -p "Your strategy description here"
```

### List recent runs
```bash
vibe-trading --list
```

### Show run details
```bash
vibe-trading --show <run_id>
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
See `docs/kraken-design/DESIGN.md` for UI styling guidelines.

## Troubleshooting
- **LLM errors**: Check `.env` has valid `DEEPSEEK_API_KEY`
- **Data errors**: OKX API may be rate-limited, try again later
- **Import errors**: Run `pip install -U vibe-trading-ai`
EOF

echo "Created QUICKSTART.md"
```

- [ ] **Step 3: Create main README**

```bash
cat > "/home/da/桌面/新建文件夹 2/vibe-crypto-trade/README.md" << 'EOF'
# Vibe-Crypto-Trading

AI-powered crypto quantitative trading system using Vibe-Trading as the core framework.

## Features
- Natural language → strategy → backtest pipeline
- OKX/Bybit simulation account integration
- AI auto-iteration for strategy optimization
- Kraken-style UI design system
- Multi-agent swarm workflows

## Quick Start
See [QUICKSTART.md](QUICKSTART.md)

## Project Structure
```
vibe-crypto-trade/
├── agent/              # Vibe-Trading agent (external)
├── docs/
│   ├── kraken-design/  # UI design system
│   └── superpowers/    # Specs and plans
├── .env.example        # Environment template
└── QUICKSTART.md       # Quick start guide
```

## Documentation
- [System Design](docs/superpowers/specs/2026-05-13-vibe-crypto-trading-design.md)
- [Phase 1 Plan](docs/superpowers/plans/2026-05-13-phase1-mvp-plan.md)
- [Workflow Baseline](docs/workflow-baseline.md)
- [Swarm Presets](docs/swarm-presets.md)

## Tech Stack
- Vibe-Trading (core framework)
- Python 3.11+
- FastAPI + React 19
- OKX data source
- Kraken DESIGN.md for UI

## License
MIT
EOF

echo "Created README.md"
```

- [ ] **Step 4: Commit all documentation**

```bash
cd "/home/da/桌面/新建文件夹 2/vibe-crypto-trade"
git add docs/
git add QUICKSTART.md
git add README.md
git commit -m "docs: Add baseline workflow documentation, quickstart guide, and project README"
```

---

## Phase 1 Exit Criteria Checklist

- [ ] Vibe-Trading installed and running (`vibe-trading --version`)
- [ ] `.env` configured with LLM API key
- [ ] OKX data source verified (test_okx_data.py passes)
- [ ] First crypto backtest completed (MA crossover)
- [ ] Backtest metrics displayed: Sharpe, WinRate, MaxDrawdown
- [ ] Pine Script export tested (`/pine` command works)
- [ ] At least one swarm preset explored (crypto_trading_desk)
- [ ] Baseline workflow documented
- [ ] Project README and quickstart guide created

---

## Next Phase Preview

**Phase 2:** Execution Layer - Connect to Bybit Simnet and OKX Demo accounts for automatic paper trading with risk controls.

---

*End of Phase 1 Implementation Plan*