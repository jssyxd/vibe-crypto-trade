"""
Streamlit Dashboard for Vibe-Crypto-Trading.
Provides real-time portfolio monitoring and backtest visualization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os

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

# Title
st.title("📊 Vibe-Crypto-Trading Dashboard")

# Sidebar
st.sidebar.header("Settings")
exchange = st.sidebar.selectbox("Exchange", ["Bybit", "OKX"])
timeframe = st.sidebar.selectbox("Timeframe", ["1D", "4H", "1H", "15m"])

# Portfolio Overview Section
st.header("Portfolio Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Value", "$100,000", "+5.2%")
with col2:
    st.metric("Daily P&L", "+$1,250", "+1.25%")
with col3:
    st.metric("Open Positions", "3", "")
with col4:
    st.metric("Sharpe Ratio", "1.45", "")

st.divider()

# Performance Chart
st.subheader("Portfolio Performance")

# Generate sample data
dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
equity = 100000 + (dates.dayofyear * 100) + (dates.dayofyear ** 1.1 * 5)
df = pd.DataFrame({'Date': dates, 'Equity': equity})

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

trades = {
    'Date': ['2024-12-15', '2024-12-14', '2024-12-13', '2024-12-12'],
    'Symbol': ['BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'BTC-USDT'],
    'Side': ['BUY', 'BUY', 'SELL', 'BUY'],
    'Quantity': [0.5, 2.0, 10.0, 0.3],
    'Price': [95000, 3500, 150, 92000],
    'P&L': ['+$500', '+$200', '-$50', '+$150']
}
df_trades = pd.DataFrame(trades)

st.dataframe(df_trades, use_container_width=True)

# Risk Dashboard
st.header("Risk Metrics")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("VaR (95%)", "$2,500")
with col2:
    st.metric("Portfolio Vol", "18.5%")
with col3:
    st.metric("Leverage", "1.0x")

# Run dashboard
if __name__ == "__main__":
    st.run()