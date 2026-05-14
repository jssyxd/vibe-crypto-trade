"""Utility functions for VCT tests.

This module provides helper functions and classes for writing tests
across the Vibe-Crypto-Trading project.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock


def create_mock_order(
    order_id: str = "TEST_ORDER_001",
    symbol: str = "BTC-USDT",
    side: str = "buy",
    order_type: str = "market",
    quantity: float = 0.1,
    price: Optional[float] = None,
    status: str = "filled",
    filled_qty: Optional[float] = None,
    avg_fill_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Create a mock order dictionary for testing.

    Args:
        order_id: Unique order identifier
        symbol: Trading symbol (e.g., BTC-USDT)
        side: Order side ('buy' or 'sell')
        order_type: Order type ('market', 'limit', 'stop')
        quantity: Order quantity
        price: Limit price (None for market orders)
        status: Order status ('pending', 'filled', 'partial', 'cancelled', 'rejected')
        filled_qty: Filled quantity (defaults to quantity if filled)
        avg_fill_price: Average fill price (defaults to price if filled)

    Returns:
        dict: Mock order data
    """
    return {
        "order_id": order_id,
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
        "status": status,
        "filled_qty": filled_qty if filled_qty is not None else quantity,
        "avg_fill_price": avg_fill_price if avg_fill_price is not None else price or 0.0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def create_mock_balance(
    total_equity: float = 100000.0,
    available: float = 90000.0,
    locked: float = 10000.0,
    positions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Create a mock balance dictionary for testing.

    Args:
        total_equity: Total account equity in USDT
        available: Available balance
        locked: Locked margin balance
        positions: List of position dictionaries

    Returns:
        dict: Mock balance data
    """
    return {
        "total_equity": total_equity,
        "available_balance": available,
        "locked_balance": locked,
        "positions": positions or [],
    }


def create_mock_position(
    symbol: str = "BTC-USDT",
    quantity: float = 0.5,
    entry_price: float = 40000.0,
    current_price: float = 45000.0,
) -> Dict[str, Any]:
    """
    Create a mock position dictionary for testing.

    Args:
        symbol: Trading symbol
        quantity: Position quantity
        entry_price: Entry price
        current_price: Current market price

    Returns:
        dict: Mock position data
    """
    unrealized_pnl = (current_price - entry_price) * quantity
    return {
        "symbol": symbol,
        "quantity": quantity,
        "entry_price": entry_price,
        "current_price": current_price,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": 0.0,
    }


def create_mock_ticker(
    symbol: str = "BTC-USDT",
    last: float = 45000.0,
    bid: float = 44990.0,
    ask: float = 45010.0,
    volume: float = 1000000.0,
) -> Dict[str, Any]:
    """
    Create a mock ticker dictionary for testing.

    Args:
        symbol: Trading symbol
        last: Last traded price
        bid: Best bid price
        ask: Best ask price
        volume: 24h trading volume

    Returns:
        dict: Mock ticker data
    """
    return {
        "symbol": symbol,
        "last": last,
        "bid": bid,
        "ask": ask,
        "volume": volume,
        "timestamp": datetime.now().isoformat(),
    }


def create_mock_signal(
    signal_id: str = "SIG001",
    symbol: str = "BTC-USDT",
    side: str = "buy",
    strategy_name: str = "TestStrategy",
    quantity: float = 0.1,
    priority: str = "NORMAL",
    reason: str = "Test signal",
) -> Dict[str, Any]:
    """
    Create a mock trading signal for testing.

    Args:
        signal_id: Unique signal identifier
        symbol: Trading symbol
        side: Signal side ('buy' or 'sell')
        strategy_name: Name of the strategy generating the signal
        quantity: Signal quantity
        priority: Signal priority ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')
        reason: Human-readable reason for the signal

    Returns:
        dict: Mock signal data
    """
    return {
        "signal_id": signal_id,
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "side": side,
        "strategy_name": strategy_name,
        "quantity": quantity,
        "priority": priority,
        "reason": reason,
    }


def assert_order_equal(actual: Dict[str, Any], expected: Dict[str, Any]) -> None:
    """
    Assert that two order dictionaries are equal (only comparing key fields).

    Args:
        actual: Actual order dictionary
        expected: Expected order dictionary

    Raises:
        AssertionError: If orders don't match
    """
    key_fields = ["order_id", "symbol", "side", "quantity", "status"]
    for field in key_fields:
        assert actual.get(field) == expected.get(field), (
            f"Order field '{field}' mismatch: "
            f"expected {expected.get(field)}, got {actual.get(field)}"
        )


def assert_portfolio_stats_valid(stats: Dict[str, Any]) -> None:
    """
    Assert that a portfolio stats dictionary has valid structure and values.

    Args:
        stats: Portfolio stats dictionary

    Raises:
        AssertionError: If stats are invalid
    """
    assert "total_value" in stats, "Missing 'total_value' in portfolio stats"
    assert "cash" in stats, "Missing 'cash' in portfolio stats"
    assert "total_pnl" in stats, "Missing 'total_pnl' in portfolio stats"
    assert stats["total_value"] >= 0, f"Invalid total_value: {stats['total_value']}"
    assert stats["cash"] >= 0, f"Invalid cash: {stats['cash']}"


class MockExchangeAdapter:
    """
    Mock exchange adapter for testing without real API connections.

    This class provides a simple in-memory simulation of exchange behavior
    for use in unit tests.
    """

    def __init__(
        self,
        initial_balance: float = 100000.0,
        initial_positions: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize mock exchange adapter.

        Args:
            initial_balance: Initial USDT balance
            initial_positions: Dict of symbol to quantity for initial positions
        """
        self._balance = initial_balance
        self._positions = initial_positions or {}
        self._orders = []
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def get_balance(self) -> Dict[str, Any]:
        return create_mock_balance(
            total_equity=self._balance,
            available=self._balance,
            locked=0.0,
        )

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        # Return a mock ticker with reasonable default values
        return create_mock_ticker(symbol=symbol)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        order = create_mock_order(
            order_id=f"MOCK_{len(self._orders) + 1:04d}",
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
        )
        self._orders.append(order)
        return order

    def get_order_status(self, order_id: str) -> str:
        for order in self._orders:
            if order["order_id"] == order_id:
                return order["status"]
        return "unknown"


def load_json_fixture(fixture_path: str) -> Dict[str, Any]:
    """
    Load a JSON fixture file for testing.

    Args:
        fixture_path: Path to JSON fixture file

    Returns:
        dict: Parsed JSON data
    """
    with open(fixture_path, "r") as f:
        return json.load(f)


def generate_timestamp_series(
    start: datetime,
    periods: int,
    freq: str = "1h",
) -> List[datetime]:
    """
    Generate a series of timestamps for testing.

    Args:
        start: Starting datetime
        periods: Number of periods to generate
        freq: Frequency ('1m', '5m', '1h', '1d')

    Returns:
        list: List of datetime objects
    """
    delta_map = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "1h": timedelta(hours=1),
        "1d": timedelta(days=1),
    }
    delta = delta_map.get(freq, timedelta(hours=1))
    return [start + i * delta for i in range(periods)]


def create_price_series(
    base_price: float = 45000.0,
    periods: int = 100,
    volatility: float = 0.02,
    trend: float = 0.0,
) -> List[float]:
    """
    Generate a simulated price series for testing.

    Args:
        base_price: Starting price
        periods: Number of price points to generate
        volatility: Price volatility (0.02 = 2%)
        trend: Trend direction (positive = upward, negative = downward)

    Returns:
        list: List of simulated prices
    """
    import random

    prices = [base_price]
    for i in range(1, periods):
        change = random.normalvariate(trend, volatility)
        new_price = prices[-1] * (1 + change)
        prices.append(max(0.01, new_price))  # Ensure positive prices
    return prices