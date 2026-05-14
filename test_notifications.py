#!/usr/bin/env python3
"""Test Notification System."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from notifications.notification_manager import NotificationManager, NotificationLevel

def test_notifications():
    print("Testing Notification System...")

    manager = NotificationManager()

    # Test all notification types
    manager.info("System Started", "Vibe-Crypto-Trading initialized")
    manager.success("Backtest Complete", "Sharpe ratio: 1.45")
    manager.alert("Risk Warning", "Position size exceeds 10%")
    manager.error("Order Failed", "Insufficient balance")
    manager.trade("BTC-USDT", "BUY", 0.5, 95000)

    print("\n All notification tests passed!")

if __name__ == "__main__":
    test_notifications()