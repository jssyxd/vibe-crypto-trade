"""
Notification Manager for trade alerts and system notifications.
Supports Telegram and console notifications.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from datetime import datetime
import os

class NotificationLevel(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TRADE = "trade"

@dataclass
class Notification:
    """Notification message."""
    level: NotificationLevel
    title: str
    message: str
    timestamp: datetime = None
    data: dict = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class TelegramNotifier:
    """Telegram notification handler."""

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def send(self, notification: Notification) -> bool:
        """Send notification via Telegram."""
        if not self.enabled:
            print(f"[TELEGRAM DISABLED] {notification.title}: {notification.message}")
            return False

        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': f"*{notification.title}*\n{notification.message}",
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False

class ConsoleNotifier:
    """Console notification handler."""

    # Color codes for terminal
    COLORS = {
        NotificationLevel.INFO: "\033[94m",     # Blue
        NotificationLevel.SUCCESS: "\033[92m",   # Green
        NotificationLevel.WARNING: "\033[93m",   # Yellow
        NotificationLevel.ERROR: "\033[91m",     # Red
        NotificationLevel.TRADE: "\033[96m",     # Cyan
    }
    RESET = "\033[0m"

    def send(self, notification: Notification) -> bool:
        """Send notification to console."""
        color = self.COLORS.get(notification.level, "")
        reset = self.RESET

        timestamp = notification.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        level_str = notification.level.value.upper()

        print(f"{color}[{timestamp}] {level_str}: {notification.title}{reset}")
        print(f"{color}  {notification.message}{reset}")

        return True

class NotificationManager:
    """
    Central notification manager.
    Routes notifications to all configured channels.
    """

    def __init__(self):
        self.handlers: List = []
        self.telegram: Optional[TelegramNotifier] = None
        self.console = ConsoleNotifier()
        self.handlers.append(self.console)

    def configure_telegram(self, bot_token: str, chat_id: str):
        """Configure Telegram notifications."""
        self.telegram = TelegramNotifier(bot_token, chat_id)
        if self.telegram.enabled:
            self.handlers.append(self.telegram)

    def send(
        self,
        level: NotificationLevel,
        title: str,
        message: str,
        data: dict = None
    ) -> bool:
        """Send notification to all handlers."""
        notification = Notification(
            level=level,
            title=title,
            message=message,
            data=data
        )

        success = True
        for handler in self.handlers:
            try:
                result = handler.send(notification)
                success = success and result
            except Exception as e:
                print(f"Handler error: {e}")
                success = False

        return success

    # Convenience methods
    def trade(self, symbol: str, side: str, quantity: float, price: float):
        """Send trade notification."""
        return self.send(
            NotificationLevel.TRADE,
            f"Trade Executed: {side}",
            f"{symbol}: {side} {quantity} @ ${price:,.2f}",
            {'symbol': symbol, 'side': side, 'quantity': quantity, 'price': price}
        )

    def alert(self, title: str, message: str):
        """Send alert notification."""
        return self.send(NotificationLevel.WARNING, title, message)

    def error(self, title: str, message: str):
        """Send error notification."""
        return self.send(NotificationLevel.ERROR, title, message)

    def info(self, title: str, message: str):
        """Send info notification."""
        return self.send(NotificationLevel.INFO, title, message)

    def success(self, title: str, message: str):
        """Send success notification."""
        return self.send(NotificationLevel.SUCCESS, title, message)