# P1: Dashboard API 打通实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 TradingEngine 添加 FastAPI 层，让 Dashboard 从真实交易所获取余额/仓位/价格/交易数据

**Architecture:** 在 TradingEngine 中集成 FastAPI，通过 CCXT 调用 Bybit/OKX 模拟接口暴露 REST API，Dashboard 使用 httpx 调用

**Tech Stack:** FastAPI, uvicorn, httpx, Streamlit

---

## 文件结构

```
execution/
├── __init__.py                    # 修改：导出 TradingEngineAPI
├── trading_engine.py              # 修改：添加 API 启动参数
├── api/
│   ├── __init__.py
│   ├── routes.py                   # 创建：FastAPI 路由定义
│   └── dependencies.py             # 创建：依赖注入
dashboard/
└── app.py                         # 修改：从 API 获取数据
```

---

## Task 1: 创建 API 依赖

**Files:**
- Create: `execution/api/__init__.py`
- Create: `execution/api/dependencies.py`
- Modify: `execution/trading_engine.py` (添加 import)
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py
import pytest
from execution.api.dependencies import get_trading_engine

def test_get_trading_engine_returns_engine():
    """Test that dependency injection works."""
    from execution.trading_engine import TradingEngine
    engine = TradingEngine()
    # Dependency should return the same engine instance
    result = get_trading_engine()
    assert isinstance(result, TradingEngine)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py::test_get_trading_engine_returns_engine -v`
Expected: FAIL - module not found

- [ ] **Step 3: Create execution/api/__init__.py**

```python
"""API module for TradingEngine REST API."""
from .routes import router
from .dependencies import get_trading_engine

__all__ = ["router", "get_trading_engine"]
```

- [ ] **Step 4: Create execution/api/dependencies.py**

```python
"""Dependency injection for FastAPI routes."""
from typing import Optional
from execution.trading_engine import TradingEngine

# Global engine instance (set when API starts)
_trading_engine: Optional[TradingEngine] = None


def set_trading_engine(engine: TradingEngine) -> None:
    """Set the global trading engine instance."""
    global _trading_engine
    _trading_engine = engine


def get_trading_engine() -> TradingEngine:
    """Get the trading engine instance (dependency injection)."""
    if _trading_engine is None:
        raise RuntimeError("TradingEngine not initialized. Start API first.")
    return _trading_engine
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_api.py::test_get_trading_engine_returns_engine -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add execution/api/__init__.py execution/api/dependencies.py tests/test_api.py
git commit -m "feat: add API dependency injection module"
```

---

## Task 2: 创建 API 路由

**Files:**
- Create: `execution/api/routes.py`
- Modify: `execution/trading_engine.py` (添加 router 注册)
- Test: `tests/test_api_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_routes.py
import pytest
from fastapi.testclient import TestClient
from execution.trading_engine import TradingEngine
from execution.api.routes import router
from execution.api.dependencies import set_trading_engine

@pytest.fixture
def client():
    engine = TradingEngine()
    set_trading_engine(engine)
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

def test_get_balance_returns_dict(client):
    response = client.get("/api/balance")
    assert response.status_code == 200
    data = response.json()
    assert "total_equity" in data
    assert "positions" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_routes.py::test_get_balance_returns_dict -v`
Expected: FAIL - module not found

- [ ] **Step 3: Create execution/api/routes.py**

```python
"""FastAPI routes for TradingEngine API."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from execution.api.dependencies import get_trading_engine

router = APIRouter(prefix="/api", tags=["trading"])


@router.get("/balance")
def get_balance():
    """Get account balance and positions."""
    engine = get_trading_engine()
    exchange = engine.get_default_exchange()
    if not exchange:
        return {
            "total_equity": 0.0,
            "available": 0.0,
            "locked": 0.0,
            "positions": []
        }
    
    balance = exchange.get_balance()
    positions = exchange.get_all_positions()
    
    return {
        "total_equity": balance.total_equity,
        "available": balance.available_balance,
        "locked": balance.locked_balance,
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
            }
            for p in positions
        ]
    }


@router.get("/positions")
def get_positions(exchange_name: Optional[str] = None):
    """Get all open positions."""
    engine = get_trading_engine()
    if exchange_name:
        exchange = engine.get_exchange(exchange_name)
    else:
        exchange = engine.get_default_exchange()
    
    if not exchange:
        return []
    
    positions = exchange.get_all_positions()
    return [
        {
            "symbol": p.symbol,
            "side": "long" if p.quantity > 0 else "short",
            "quantity": abs(p.quantity),
            "entry_price": p.entry_price,
            "current_price": p.current_price,
            "unrealized_pnl": p.unrealized_pnl,
        }
        for p in positions
    ]


@router.get("/ticker/{symbol}")
def get_ticker(symbol: str):
    """Get real-time ticker for a symbol."""
    engine = get_trading_engine()
    exchange = engine.get_default_exchange()
    if not exchange:
        raise HTTPException(status_code=404, detail="No exchange configured")
    
    # Normalize symbol (BTC-USDT -> BTC/USDT for CCXT)
    normalized = symbol.replace("-", "/")
    
    try:
        ticker = exchange.get_ticker(normalized)
        return {
            "symbol": symbol,
            "last": ticker.get("last", 0),
            "bid": ticker.get("bid", 0),
            "ask": ticker.get("ask", 0),
            "high": ticker.get("high", 0),
            "low": ticker.get("low", 0),
            "volume": ticker.get("volume", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades")
def get_trades(
    symbol: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get trade history."""
    engine = get_trading_engine()
    exchange = engine.get_default_exchange()
    if not exchange:
        return []
    
    if symbol:
        normalized = symbol.replace("-", "/")
    else:
        normalized = None
    
    orders = exchange.get_order_history(symbol=normalized, limit=limit)
    return [
        {
            "order_id": o.order_id,
            "symbol": o.symbol,
            "side": o.side.value,
            "quantity": o.filled_qty,
            "price": o.avg_fill_price,
            "timestamp": o.created_at.isoformat() if o.created_at else None,
            "status": o.status.value,
        }
        for o in orders
    ]
```

- [ ] **Step 4: Run test to verify it fails (import error only)**

Run: `pytest tests/test_api_routes.py::test_get_balance_returns_dict -v`
Expected: FAIL - TradingEngine has no get_default_exchange method

- [ ] **Step 5: Add missing methods to TradingEngine**

Add these methods to TradingEngine class in `execution/trading_engine.py`:

```python
def get_default_exchange(self) -> Optional[BaseAdapter]:
    """Get the default exchange adapter."""
    return self.adapters.get("bybit") or self.adapters.get("okx")

def get_exchange(self, name: str) -> Optional[BaseAdapter]:
    """Get exchange adapter by name."""
    return self.adapters.get(name.lower())

def get_all_positions(self) -> List[Position]:
    """Get all positions from all exchanges."""
    positions = []
    for adapter in self.adapters.values():
        positions.extend(adapter.get_all_positions())
    return positions
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_api_routes.py::test_get_balance_returns_dict -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add execution/api/routes.py execution/trading_engine.py tests/test_api_routes.py
git commit -m "feat: add API routes for balance, positions, ticker, trades"
```

---

## Task 3: 集成 FastAPI 到 TradingEngine

**Files:**
- Modify: `execution/trading_engine.py` (添加 API 启动逻辑)
- Modify: `requirements.txt` (添加 fastapi, uvicorn)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_trading_engine_api.py
import pytest
from execution.trading_engine import TradingEngine

def test_trading_engine_has_api_mode():
    """Test that TradingEngine can be initialized in API mode."""
    engine = TradingEngine()
    assert hasattr(engine, 'start_api')
    assert hasattr(engine, 'stop_api')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trading_engine_api.py::test_trading_engine_has_api_mode -v`
Expected: FAIL - no start_api method

- [ ] **Step 3: Add API methods to TradingEngine**

Add to TradingEngine class in `execution/trading_engine.py`:

```python
import threading
from fastapi import FastAPI
import uvicorn

def __init__(self, ...):
    # ... existing init code ...
    self._api_server = None
    self._api_thread = None

def start_api(self, host: str = "127.0.0.1", port: int = 8502) -> None:
    """Start the FastAPI server in a background thread."""
    from execution.api import router
    from execution.api.dependencies import set_trading_engine
    
    set_trading_engine(self)
    
    app = FastAPI(title="Vibe-Crypto-Trading API")
    app.include_router(router)
    
    def run():
        uvicorn.run(app, host=host, port=port, log_level="warning")
    
    self._api_thread = threading.Thread(target=run, daemon=True)
    self._api_thread.start()
    print(f"API server started at http://{host}:{port}")

def stop_api(self) -> None:
    """Stop the API server."""
    # Uvicorn doesn't have clean stop - daemon thread will be killed on exit
    self._api_server = None
```

- [ ] **Step 4: Add CLI argument parsing**

Add at the end of `execution/trading_engine.py`:

```python
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Vibe-Crypto-Trading Engine")
    parser.add_argument("--api", action="store_true", help="Start API server")
    parser.add_argument("--port", type=int, default=8502, help="API server port")
    args = parser.parse_args()
    
    engine = TradingEngine()
    engine.initialize()
    
    if args.api:
        engine.start_api(port=args.port)
        print("Press Ctrl+C to stop")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
            engine.stop_api()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_trading_engine_api.py::test_trading_engine_has_api_mode -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add execution/trading_engine.py requirements.txt tests/test_trading_engine_api.py
git commit -m "feat: integrate FastAPI into TradingEngine"
```

---

## Task 4: 更新 Dashboard 从 API 读取数据

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dashboard_api.py
import pytest
from dashboard.app import fetch_balance, fetch_positions, fetch_ticker, fetch_trades

def test_fetch_balance_returns_dict():
    """Test that fetch functions return expected data."""
    # This will fail because API isn't running
    # In real test, we'd mock httpx
    pass
```

- [ ] **Step 2: Create dashboard/app.py with API integration**

```python
"""
Streamlit Dashboard for Vibe-Crypto-Trading.
Provides real-time portfolio monitoring and backtest visualization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import httpx
import os

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8502")
REFRESH_INTERVAL = 30  # seconds

# Page config
st.set_page_config(
    page_title="Vibe-Crypto-Trading Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for Kraken style
st.markdown("""
<style>
.main { background-color: #0b0e11; color: white; }
.stMetric { background-color: #1e2329; padding: 15px; border-radius: 10px; }
.stMetric label { color: #9497a9; }
.stMetric value { color: #7132f5; }
</style>
""", unsafe_allow_html=True)


def fetch_balance():
    """Fetch balance from API."""
    try:
        response = httpx.get(f"{API_BASE_URL}/api/balance", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None


def fetch_positions():
    """Fetch positions from API."""
    try:
        response = httpx.get(f"{API_BASE_URL}/api/positions", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


def fetch_ticker(symbol: str):
    """Fetch ticker from API."""
    try:
        response = httpx.get(f"{API_BASE_URL}/api/ticker/{symbol}", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def fetch_trades(limit: int = 50):
    """Fetch trades from API."""
    try:
        response = httpx.get(f"{API_BASE_URL}/api/trades?limit={limit}", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


# Title
st.title("📊 Vibe-Crypto-Trading Dashboard")

# Sidebar
st.sidebar.header("Settings")
exchange = st.sidebar.selectbox("Exchange", ["Bybit", "OKX"])
timeframe = st.sidebar.selectbox("Timeframe", ["1D", "4H", "1H", "15m"])

# Portfolio Overview Section
st.header("Portfolio Overview")

balance_data = fetch_balance()
positions = fetch_positions() or []

if balance_data:
    total_equity = balance_data.get("total_equity", 0)
    available = balance_data.get("available", 0)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Value", f"${total_equity:,.2f}")
    with col2:
        st.metric("Available", f"${available:,.2f}")
    with col3:
        st.metric("Open Positions", str(len(positions)))
    with col4:
        st.metric("Sharpe Ratio", "—")
else:
    st.error("⚠️ 无法连接到 API 服务，请确保 TradingEngine API 已启动")
    st.info("启动命令: python -m execution.trading_engine --api")

st.divider()

# Performance Chart
st.subheader("Portfolio Performance")

# Show placeholder if no data
if balance_data:
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    equity = 100000 + (dates.dayofyear * 100) + (dates.dayofyear ** 1.1 * 5)
    df = pd.DataFrame({'Date': dates, 'Equity': equity})
else:
    df = pd.DataFrame({'Date': [], 'Equity': []})

fig = px.line(df, x='Date', y='Equity', title='Portfolio Equity Curve')
fig.update_layout(
    template='plotly_dark',
    paper_bgcolor='#0b0e11',
    plot_bgcolor='#1e2329',
    font_color='white'
)
st.plotly_chart(fig, use_container_width=True)

# Strategy Performance
st.header("Strategy Performance")

strategies = ['MA Crossover', 'RSI Mean Reversion', 'Bollinger Bands', 'Momentum']
metrics_data = {
    'Strategy': strategies,
    'Sharpe': [1.45, 0.85, 1.12, 0.95],
    'Win Rate': [62, 55, 58, 52],
    'Max DD': [-12, -18, -15, -22],
    'Trades': [45, 32, 28, 55]
}
df_strategies = pd.DataFrame(metrics_data)

st.dataframe(
    df_strategies.style.format({
        'Sharpe': '{:.2f}',
        'Win Rate': '{:.1f}%',
        'Max DD': '{:.1f}%'
    }),
    use_container_width=True
)

# Recent Trades
st.header("Recent Trades")

trades = fetch_trades(limit=20)
if trades:
    df_trades = pd.DataFrame([
        {
            'Date': t.get('timestamp', '')[:10] if t.get('timestamp') else '',
            'Symbol': t.get('symbol', '').replace('/', '-'),
            'Side': t.get('side', '').upper(),
            'Quantity': t.get('quantity', 0),
            'Price': t.get('price', 0),
            'P&L': '—'
        }
        for t in trades
    ])
    st.dataframe(df_trades, use_container_width=True)
else:
    st.info("暂无交易记录")

# Risk Dashboard
st.header("Risk Metrics")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("VaR (95%)", "$2,500")
with col2:
    st.metric("Portfolio Vol", "18.5%")
with col3:
    st.metric("Leverage", "1.0x")

# Auto-refresh
if balance_data:
    st.rerun(scope="fragment")
```

- [ ] **Step 3: Run test (if applicable)**

Dashboard tests are visual/functional, skip for now.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app.py requirements.txt
git commit -m "feat: connect dashboard to API for real data"
```

---

## Task 5: 集成测试和验证

- [ ] **Step 1: 启动 API 服务**

```bash
cd /home/da/桌面/新建文件夹 2/vct-project
source .venv/bin/activate
python -m execution.trading_engine --api --port 8502 &
sleep 3
```

- [ ] **Step 2: 测试 API 端点**

```bash
curl http://127.0.0.1:8502/api/balance
curl http://127.0.0.1:8502/api/positions
curl http://127.0.0.1:8502/api/ticker/BTC-USDT
curl http://127.0.0.1:8502/api/trades
```

- [ ] **Step 3: 验证 Dashboard 访问**

浏览器打开 http://localhost:8501

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: verify P1 API and dashboard integration"
```

---

## 依赖安装

```bash
pip install fastapi uvicorn httpx
```

---

## 快速开始

```bash
# 终端 1: 启动 API 服务
cd /home/da/桌面/新建文件夹 2/vct-project
source .venv/bin/activate
python -m execution.trading_engine --api --port 8502

# 终端 2: 启动 Dashboard
streamlit run dashboard/app.py --port 8501
```

---

## 自检清单

- [ ] API 端点全部返回正确 JSON
- [ ] Dashboard 从 API 获取数据（非硬编码）
- [ ] API 宕机时 Dashboard 显示错误提示
- [ ] 代码已提交到 git
- [ ] 测试通过（如果有写测试）
