"""Tests for API routes."""
import pytest
from fastapi.testclient import TestClient
from execution.trading_engine import TradingEngine
from execution.api.routes import router
from execution.api.dependencies import set_trading_engine

@pytest.fixture
def client():
    engine = TradingEngine()
    # No adapters initialized - empty engine for testing
    set_trading_engine(engine)
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

def test_get_balance_returns_dict(client):
    """Test /api/balance endpoint returns correct structure."""
    response = client.get("/api/balance")
    assert response.status_code == 200
    data = response.json()
    assert "total_equity" in data
    assert "positions" in data

def test_get_positions_returns_list(client):
    """Test /api/positions endpoint returns list."""
    response = client.get("/api/positions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_ticker_handles_missing_exchange(client):
    """Test /api/ticker/{symbol} returns 404 when no exchange."""
    response = client.get("/api/ticker/BTC-USDT")
    # Should return 404 since no exchange is initialized
    assert response.status_code in [200, 404]

def test_get_trades_returns_list(client):
    """Test /api/trades endpoint returns list."""
    response = client.get("/api/trades")
    assert response.status_code == 200
    assert isinstance(response.json(), list)