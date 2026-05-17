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