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