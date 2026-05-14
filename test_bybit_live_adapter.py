#!/usr/bin/env python3
"""Test Bybit Live Adapter."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execution.adapters.bybit_live_adapter import BybitLiveAdapter

def test_live_adapter():
    adapter = BybitLiveAdapter(testnet=True)

    print("Testing Bybit Live Adapter...")

    # Connect
    connected = adapter.connect()
    print(f"Connected: {connected}")

    if not connected:
        print("Failed to connect to Bybit")
        return

    # Get price
    price = adapter.get_current_price("BTC-USDT")
    print(f"BTC Price: ${price:,.2f}" if price else "Price: N/A")

    # Get order book
    ob = adapter.get_order_book("BTC-USDT", 5)
    if ob:
        print(f"Top bid: ${ob['bids'][0][0]:,.2f}" if ob['bids'] else "No bids")
        print(f"Top ask: ${ob['asks'][0][0]:,.2f}" if ob['asks'] else "No asks")

    # Get recent trades
    trades = adapter.get_recent_trades("BTC-USDT", 5)
    print(f"Recent trades: {len(trades)}")

    # Get 24h stats
    stats = adapter.get_24h_stats("BTC-USDT")
    if stats:
        print(f"24h High: ${stats.get('high', 'N/A')}")
        print(f"24h Low: ${stats.get('low', 'N/A')}")

    # Get kline data
    klines = adapter.get_kline("BTC-USDT", '1h', 10)
    print(f"Klines fetched: {len(klines)}")

    adapter.disconnect()
    print("Disconnected")

if __name__ == "__main__":
    test_live_adapter()