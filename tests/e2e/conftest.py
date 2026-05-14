"""Pytest configuration for E2E tests.

This module provides fixtures specifically for end-to-end testing
of complete trading flows in the VCT system.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def e2e_project_root():
    """Provide the project root for E2E tests."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def e2e_config():
    """
    Provide E2E test configuration.

    Returns:
        dict: Configuration dictionary with test settings.
    """
    return {
        "testnet": True,
        "initial_capital": 100000.0,
        "max_position_size": 0.1,
        "max_daily_loss_pct": 0.05,
        "symbols": ["BTC-USDT", "ETH-USDT"],
        "strategies": ["MA_Cross", "RSI_Oversold", "Momentum"],
    }


@pytest.fixture
def e2e_mock_exchange(mocker):
    """
    Provide a fully mocked exchange for E2E testing.

    This fixture creates a complete mock exchange that simulates
    all trading behavior without requiring real API connections.

    Returns:
        MagicMock: A fully configured mock exchange adapter.
    """
    from execution.adapters.base_adapter import (
        Order, OrderSide, OrderType, OrderStatus,
        AccountBalance, Position
    )

    mock_exchange = MagicMock()

    # Configure balance
    mock_balance = AccountBalance(
        total_equity=100000.0,
        available_balance=95000.0,
        locked_balance=5000.0,
        positions={
            "BTC-USDT": Position(
                symbol="BTC-USDT",
                quantity=0.5,
                entry_price=40000.0,
                current_price=45000.0,
                unrealized_pnl=2500.0,
                realized_pnl=0.0,
            ),
            "ETH-USDT": Position(
                symbol="ETH-USDT",
                quantity=5.0,
                entry_price=2500.0,
                current_price=2750.0,
                unrealized_pnl=1250.0,
                realized_pnl=0.0,
            ),
        },
    )
    mock_exchange.get_balance.return_value = mock_balance

    # Configure tickers for all symbols
    mock_exchange.get_ticker.side_effect = lambda symbol: {
        "BTC-USDT": {"symbol": "BTC-USDT", "last": 45000.0, "bid": 44990.0, "ask": 45010.0},
        "ETH-USDT": {"symbol": "ETH-USDT", "last": 2750.0, "bid": 2749.0, "ask": 2751.0},
    }.get(symbol, {"symbol": symbol, "last": 100.0, "bid": 99.0, "ask": 101.0})

    # Configure order placement
    order_counter = [0]

    def place_order_impl(symbol, side, order_type, quantity, price=None):
        order_counter[0] += 1
        fill_price = price or 45000.0  # Default fill price
        return Order(
            order_id=f"E2E_ORDER_{order_counter[0]:04d}",
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.FILLED,
            filled_qty=quantity,
            avg_fill_price=fill_price,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    mock_exchange.place_order.side_effect = place_order_impl
    mock_exchange.connect.return_value = True
    mock_exchange.disconnect.return_value = True

    return mock_exchange


@pytest.fixture
def e2e_portfolio_manager():
    """
    Provide a portfolio manager for E2E testing.

    Returns:
        PortfolioManager: A configured portfolio manager instance.
    """
    from portfolio.portfolio_manager import PortfolioManager, AllocationStrategy

    pm = PortfolioManager(
        initial_capital=100000.0,
        max_strategies=10,
        allocation_strategy=AllocationStrategy.EQUAL_WEIGHT,
    )

    # Add some strategy allocations
    pm.add_strategy_allocation("MA_Cross", 0.3)
    pm.add_strategy_allocation("RSI_Oversold", 0.25)
    pm.add_strategy_allocation("Momentum", 0.2)

    return pm


@pytest.fixture
def e2e_risk_controller():
    """
    Provide a risk controller for E2E testing.

    Returns:
        RiskController: A configured risk controller instance.
    """
    from execution.risk.risk_controller import RiskController, RiskLimits

    limits = RiskLimits(
        max_position_pct=0.1,
        max_leverage=1.0,
        max_drawdown_daily=0.05,
        max_drawdown_weekly=0.10,
        max_drawdown_monthly=0.20,
        max_total_positions=5,
    )
    return RiskController(limits=limits)


@pytest.fixture
def e2e_signal_queue(tmp_path):
    """
    Provide a signal queue for E2E testing.

    Args:
        tmp_path: Pytest tmp_path fixture

    Returns:
        SignalQueue: A configured signal queue instance.
    """
    from execution.signals.signal_queue import SignalQueue

    queue_path = tmp_path / "e2e_test_queue.json"
    return SignalQueue(storage_path=str(queue_path))


@pytest.fixture
def e2e_sample_signals():
    """
    Provide a list of sample trading signals for E2E testing.

    Returns:
        list: List of sample trading signals.
    """
    from execution.signals.signal_queue import TradingSignal, SignalPriority

    base_time = datetime.now()
    return [
        TradingSignal(
            signal_id="E2E_SIG_001",
            timestamp=base_time,
            symbol="BTC-USDT",
            side="buy",
            strategy_name="MA_Cross",
            quantity=0.1,
            priority=SignalPriority.NORMAL,
        ),
        TradingSignal(
            signal_id="E2E_SIG_002",
            timestamp=base_time + timedelta(minutes=5),
            symbol="ETH-USDT",
            side="sell",
            strategy_name="RSI_Oversold",
            quantity=1.0,
            priority=SignalPriority.HIGH,
        ),
        TradingSignal(
            signal_id="E2E_SIG_003",
            timestamp=base_time + timedelta(minutes=10),
            symbol="BTC-USDT",
            side="sell",
            strategy_name="Momentum",
            quantity=0.05,
            priority=SignalPriority.LOW,
        ),
    ]


@pytest.fixture
def e2e_market_data():
    """
    Provide mock market data for E2E testing.

    Returns:
        dict: Dictionary of market data by symbol.
    """
    return {
        "BTC-USDT": {
            "last": 45000.0,
            "bid": 44990.0,
            "ask": 45010.0,
            "volume": 1500000000.0,
            "change_24h": 0.025,
            "high_24h": 46000.0,
            "low_24h": 44000.0,
        },
        "ETH-USDT": {
            "last": 2750.0,
            "bid": 2749.0,
            "ask": 2751.0,
            "volume": 800000000.0,
            "change_24h": -0.015,
            "high_24h": 2800.0,
            "low_24h": 2700.0,
        },
    }