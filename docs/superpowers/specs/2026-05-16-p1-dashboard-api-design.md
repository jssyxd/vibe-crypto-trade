# P1: Dashboard 打通 — API 层 + Dashboard 改造

## 日期: 2026-05-16

## 目标

让 Dashboard 从硬编码样例数据改为显示真实的：
- 账户余额
- 持仓信息
- 实时价格
- 交易历史

## 架构

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Streamlit      │  HTTP   │  TradingEngine  │  CCXT   │  Bybit/OKX      │
│  Dashboard      │ ──────► │  + FastAPI      │ ──────► │  API            │
│  (Port 8501)    │         │  (Port 8502)   │         │  (Simnet)       │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

## API 端点

### GET /api/balance
返回账户余额信息。

**响应:**
```json
{
  "total_equity": 100000.0,
  "available": 95000.0,
  "locked": 5000.0,
  "positions": [
    {
      "symbol": "BTC-USDT",
      "quantity": 0.5,
      "entry_price": 80000.0,
      "current_price": 85000.0,
      "unrealized_pnl": 2500.0
    }
  ]
}
```

### GET /api/positions
返回所有持仓。

**响应:**
```json
[
  {
    "symbol": "BTC-USDT",
    "side": "long",
    "quantity": 0.5,
    "entry_price": 80000.0,
    "current_price": 85000.0,
    "unrealized_pnl": 2500.0
  }
]
```

### GET /api/ticker/{symbol}
返回指定交易对的实时价格。

**响应:**
```json
{
  "symbol": "BTC-USDT",
  "last": 85000.0,
  "bid": 84999.0,
  "ask": 85001.0,
  "high": 86000.0,
  "low": 84000.0,
  "volume": 12345.67
}
```

### GET /api/trades
返回交易历史。

**响应:**
```json
[
  {
    "order_id": "BYBIT_TEST_123",
    "symbol": "BTC-USDT",
    "side": "buy",
    "quantity": 0.1,
    "price": 80000.0,
    "timestamp": "2026-05-16T10:00:00Z",
    "status": "filled"
  }
]
```

## 组件

### 1. API 模块 (新增)
**文件:** `execution/api/` 目录

- `__init__.py`
- `routes.py` — FastAPI 路由定义
- `dependencies.py` — 依赖注入（获取 TradingEngine 实例）

### 2. TradingEngine 修改
**文件:** `execution/trading_engine.py`

- 添加 FastAPI 实例
- 注册路由
- 支持 `--api` 启动参数

### 3. Dashboard 修改
**文件:** `dashboard/app.py`

- 移除硬编码数据
- 添加 `httpx` 调用 API 端点
- 添加实时刷新（`st.rerun` 或 `@st.fragment`）

## 启动方式

```bash
# 终端 1: 启动 API 服务
cd /home/da/桌面/新建文件夹 2/vct-project
source .venv/bin/activate
python -m execution.trading_engine --api --port 8502

# 终端 2: 启动 Dashboard
streamlit run dashboard/app.py --port 8501
```

## 数据流

1. Dashboard 加载时调用 `GET /api/balance` 获取余额
2. 调用 `GET /api/positions` 获取持仓
3. 调用 `GET /api/ticker/BTC-USDT` 获取实时价格
4. 调用 `GET /api/trades` 获取交易历史
5. 每 30 秒自动刷新数据

## 回退机制

如果 API 不可用：
- Dashboard 显示 "连接失败，请检查 API 服务"
- 不显示硬编码数据

## 安全

- API 默认仅监听 localhost
- 不暴露私钥，所有交易所调用使用 Read-only API Key
- 可选：添加 `X-API-Key` 认证头

## 依赖

```python
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
httpx>=0.25.0
```

## 测试

1. 启动 API 服务
2. 测试所有端点返回正确 JSON
3. 启动 Dashboard 验证数据显示
4. 模拟 API 宕机验证错误处理
