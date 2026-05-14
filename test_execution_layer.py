#!/usr/bin/env python3
"""
Test script for Execution Layer.

Tests:
1. Exchange adapters (Bybit, OKX)
2. Risk controller
3. Signal queue
4. Execution engine
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execution.adapters import BybitAdapter, OKXAdapter
from execution.risk.risk_controller import RiskController, RiskLimits
from execution.signals.signal_queue import SignalQueue, TradingSignal, SignalPriority
from execution.core.execution_engine import ExecutionEngine
from datetime import datetime


def test_bybit_adapter():
    """Test Bybit adapter."""
    print("\n" + "="*60)
    print("Testing Bybit Adapter")
    print("="*60)

    adapter = BybitAdapter(testnet=True)
    connected = adapter.connect()
    print(f"Connected: {connected}")

    # Get balance
    balance = adapter.get_balance()
    print(f"Balance: {balance.total_equity:.2f} USDT")

    # Get ticker
    ticker = adapter.get_ticker("BTC-USDT")
    print(f"BTC Price: ${ticker.get('last', 0):,.2f}")

    # Place test order
    from execution.adapters.base_adapter import OrderSide, OrderType
    order = adapter.place_order(
        symbol="BTC-USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.01,
    )
    print(f"Order placed: {order.order_id}, Status: {order.status.value}")
    print(f"  Filled: {order.filled_qty} @ ${order.avg_fill_price:,.2f}")

    return True


def test_okx_adapter():
    """Test OKX adapter."""
    print("\n" + "="*60)
    print("Testing OKX Adapter")
    print("="*60)

    adapter = OKXAdapter(testnet=True)
    connected = adapter.connect()
    print(f"Connected: {connected}")

    # Get balance
    balance = adapter.get_balance()
    print(f"Balance: {balance.total_equity:.2f} USDT")

    # Get ticker
    ticker = adapter.get_ticker("BTC-USDT")
    print(f"BTC Price: ${ticker.get('last', 0):,.2f}")

    return True


def test_risk_controller():
    """Test Risk Controller."""
    print("\n" + "="*60)
    print("Testing Risk Controller")
    print("="*60)

    risk = RiskController()

    # Test order approval
    result = risk.check_order(
        symbol="BTC-USDT",
        side="buy",
        quantity=0.1,
        price=80000,
        portfolio_value=100000,
    )
    print(f"Order check: approved={result.approved}, message={result.message}")

    # Update metrics to trigger drawdown
    risk.update_metrics(95000, {'BTC-USDT': 0.1})
    status = risk.get_status()
    print(f"Risk status: {status}")

    return True


def test_signal_queue():
    """Test Signal Queue."""
    print("\n" + "="*60)
    print("Testing Signal Queue")
    print("="*60)

    queue = SignalQueue(storage_path="execution/signals/test_queue.json")

    # Add signals
    signal1 = TradingSignal(
        signal_id="SIG001",
        timestamp=datetime.now(),
        symbol="BTC-USDT",
        side="buy",
        strategy_name="MA_Cross",
        quantity=0.01,
        priority=SignalPriority.NORMAL,
    )
    queue.add(signal1)

    signal2 = TradingSignal(
        signal_id="SIG002",
        timestamp=datetime.now(),
        symbol="ETH-USDT",
        side="sell",
        strategy_name="RSI_Oversold",
        quantity=1.0,
        priority=SignalPriority.HIGH,
    )
    queue.add(signal2)

    # Get stats
    stats = queue.get_stats()
    print(f"Queue stats: {stats}")

    # Get next signal
    next_sig = queue.get_next()
    print(f"Next signal: {next_sig.signal_id} ({next_sig.symbol}), Priority: {next_sig.priority.name}")

    # Clean up
    os.remove("execution/signals/test_queue.json")

    return True


def test_execution_engine():
    """Test Execution Engine."""
    print("\n" + "="*60)
    print("Testing Execution Engine")
    print("="*60)

    # Create engine with Bybit
    engine = ExecutionEngine(exchange="bybit", testnet=True)
    connected = engine.connect()
    print(f"Connected: {connected}")

    # Get status
    status = engine.get_status()
    print(f"Engine status: exchange={status['exchange']}, connected={status['connected']}")
    print(f"  Balance: {status['balance']['total']:.2f} USDT")
    print(f"  Risk: {status['risk']['daily_drawdown']}")

    # Add a signal
    signal = TradingSignal(
        signal_id="ENG001",
        timestamp=datetime.now(),
        symbol="BTC-USDT",
        side="buy",
        strategy_name="TestStrategy",
        quantity=0.01,
        priority=SignalPriority.NORMAL,
    )

    print(f"\nProcessing signal: {signal.signal_id}")
    result = engine.process_signal(signal)
    print(f"Result: status={result['status']}, order_id={result.get('order_id')}")
    print(f"Message: {result['message']}")

    return True


def main():
    print("="*60)
    print("Vibe-Crypto-Trading Execution Layer Test")
    print("="*60)

    tests = [
        ("Bybit Adapter", test_bybit_adapter),
        ("OKX Adapter", test_okx_adapter),
        ("Risk Controller", test_risk_controller),
        ("Signal Queue", test_signal_queue),
        ("Execution Engine", test_execution_engine),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"\n❌ {name} FAILED: {e}")
            results.append((name, f"FAIL: {e}"))

    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    for name, result in results:
        status = "✅" if "PASS" in result else "❌"
        print(f"{status} {name}: {result}")

    all_passed = all("PASS" in r for _, r in results)
    print("\n" + ("✅ ALL TESTS PASSED!" if all_passed else "❌ SOME TESTS FAILED"))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
