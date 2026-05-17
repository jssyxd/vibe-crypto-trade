"""Tests for TradingEngine API integration."""
import pytest
from execution.trading_engine import TradingEngine


def test_trading_engine_has_api_mode():
    """Test that TradingEngine has API methods."""
    engine = TradingEngine()
    assert hasattr(engine, 'start_api')
    assert hasattr(engine, 'stop_api')


def test_trading_engine_api_thread_safe():
    """Test that start_api doesn't block."""
    engine = TradingEngine()
    # Should start without blocking
    engine.start_api(port=8502)
    assert engine._api_thread is not None
    assert engine._api_thread.daemon is True