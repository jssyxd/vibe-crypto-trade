"""Pytest configuration for tests directory."""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def vct_project():
    """
    Fixture providing the project root directory path.

    Returns:
        Path: Absolute path to the project root.
    """
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def sample_portfolio():
    """
    Fixture providing a sample portfolio state for testing.

    Returns:
        dict: A dictionary representing a sample portfolio with:
            - initial_capital: float
            - cash: float
            - positions: list of position dicts
            - strategy_allocations: dict of strategy names to allocation percentages
    """
    return {
        "initial_capital": 100000.0,
        "cash": 75000.0,
        "positions": [
            {
                "strategy_name": "MA_Cross",
                "symbol": "BTC-USDT",
                "quantity": 0.5,
                "entry_price": 40000.0,
                "current_price": 45000.0,
                "unrealized_pnl": 2500.0,
                "allocation_pct": 0.25,
            },
            {
                "strategy_name": "RSI_Oversold",
                "symbol": "ETH-USDT",
                "quantity": 5.0,
                "entry_price": 2500.0,
                "current_price": 2750.0,
                "unrealized_pnl": 1250.0,
                "allocation_pct": 0.15,
            },
        ],
        "strategy_allocations": {
            "MA_Cross": 0.3,
            "RSI_Oversold": 0.25,
            "Momentum": 0.2,
        },
    }


@pytest.fixture
def sample_strategy():
    """
    Fixture providing a sample strategy configuration for testing.

    Returns:
        dict: A dictionary representing a trading strategy with:
            - name: strategy name
            - parameters: dict of strategy parameters
            - signals: list of generated signals
    """
    return {
        "name": "TestStrategy",
        "type": "MA_Cross",
        "parameters": {
            "fast_period": 10,
            "slow_period": 20,
            "signal_threshold": 0.01,
        },
        "signals": [
            {
                "signal_id": "SIG001",
                "timestamp": "2024-01-15T10:00:00",
                "symbol": "BTC-USDT",
                "side": "buy",
                "quantity": 0.1,
                "priority": "NORMAL",
                "reason": "MA_Cross_Bullish",
            },
            {
                "signal_id": "SIG002",
                "timestamp": "2024-01-15T12:00:00",
                "symbol": "ETH-USDT",
                "side": "sell",
                "quantity": 1.0,
                "priority": "HIGH",
                "reason": "RSI_Overbought",
            },
        ],
    }


@pytest.fixture
def mock_bybit_adapter(mocker):
    """
    Fixture providing a mocked Bybit adapter for testing.

    Returns:
        MagicMock: A mocked BybitAdapter instance with common methods stubbed.
    """
    from execution.adapters.base_adapter import (
        Order, OrderSide, OrderType, OrderStatus,
        AccountBalance, Position
    )
    from datetime import datetime

    # Create mock adapter
    mock_adapter = mocker.MagicMock()

    # Configure mock balance
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
            )
        },
    )
    mock_adapter.get_balance.return_value = mock_balance

    # Configure mock ticker
    mock_adapter.get_ticker.return_value = {
        "symbol": "BTC-USDT",
        "last": 45000.0,
        "bid": 44990.0,
        "ask": 45010.0,
        "volume": 1000000.0,
    }

    # Configure mock order placement
    def place_order_mock(symbol, side, order_type, quantity, price=None):
        return Order(
            order_id=f"MOCK_ORDER_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.FILLED,
            filled_qty=quantity,
            avg_fill_price=price or 45000.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    mock_adapter.place_order.side_effect = place_order_mock
    mock_adapter.connect.return_value = True
    mock_adapter.disconnect.return_value = True
    mock_adapter.get_position.return_value = Position(
        symbol="BTC-USDT",
        quantity=0.5,
        entry_price=40000.0,
        current_price=45000.0,
        unrealized_pnl=2500.0,
        realized_pnl=0.0,
    )

    return mock_adapter


@pytest.fixture
def mock_okx_adapter(mocker):
    """
    Fixture providing a mocked OKX adapter for testing.

    Returns:
        MagicMock: A mocked OKXAdapter instance with common methods stubbed.
    """
    from execution.adapters.base_adapter import (
        Order, OrderSide, OrderType, OrderStatus,
        AccountBalance, Position
    )
    from datetime import datetime

    # Create mock adapter
    mock_adapter = mocker.MagicMock()

    # Configure mock balance
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
            )
        },
    )
    mock_adapter.get_balance.return_value = mock_balance

    # Configure mock ticker
    mock_adapter.get_ticker.return_value = {
        "symbol": "BTC-USDT",
        "last": 45000.0,
        "bid": 44990.0,
        "ask": 45010.0,
        "volume": 1000000.0,
    }

    # Configure mock order placement
    def place_order_mock(symbol, side, order_type, quantity, price=None):
        return Order(
            order_id=f"OKX_MOCK_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.FILLED,
            filled_qty=quantity,
            avg_fill_price=price or 45000.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    mock_adapter.place_order.side_effect = place_order_mock
    mock_adapter.connect.return_value = True
    mock_adapter.disconnect.return_value = True
    mock_adapter.get_position.return_value = Position(
        symbol="BTC-USDT",
        quantity=0.5,
        entry_price=40000.0,
        current_price=45000.0,
        unrealized_pnl=2500.0,
        realized_pnl=0.0,
    )

    return mock_adapter


@pytest.fixture
def temp_data_dir(tmp_path):
    """
    Fixture providing a temporary directory for test data.

    Returns:
        Path: Path to temporary directory that is cleaned up after tests.
    """
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_order():
    """
    Fixture providing a sample order for testing.

    Returns:
        Order: A sample Order object.
    """
    from execution.adapters.base_adapter import Order, OrderSide, OrderType, OrderStatus
    from datetime import datetime

    return Order(
        order_id="TEST_ORDER_001",
        symbol="BTC-USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
        price=None,
        status=OrderStatus.FILLED,
        filled_qty=0.1,
        avg_fill_price=45000.0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_trading_signal():
    """
    Fixture providing a sample trading signal for testing.

    Returns:
        dict: A dictionary representing a trading signal.
    """
    from datetime import datetime

    return {
        "signal_id": "SIG_TEST_001",
        "timestamp": datetime.now().isoformat(),
        "symbol": "BTC-USDT",
        "side": "buy",
        "strategy_name": "TestStrategy",
        "quantity": 0.1,
        "priority": "NORMAL",
        "reason": "MA_Cross_Bullish",
    }