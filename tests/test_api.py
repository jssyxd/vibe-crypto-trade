"""Tests for API dependency injection."""
import pytest
from execution.api.dependencies import get_trading_engine, set_trading_engine
from execution.trading_engine import TradingEngine


def test_get_trading_engine_returns_engine():
    """Test that dependency injection works."""
    engine = TradingEngine()
    set_trading_engine(engine)
    result = get_trading_engine()
    assert isinstance(result, TradingEngine)
    assert result is engine


def test_get_trading_engine_raises_when_not_set():
    """Test that accessing engine before initialization raises."""
    # Reset global state for this test
    import execution.api.dependencies as deps
    deps._trading_engine = None

    with pytest.raises(RuntimeError, match="TradingEngine not initialized"):
        get_trading_engine()