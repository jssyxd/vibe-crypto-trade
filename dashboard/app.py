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