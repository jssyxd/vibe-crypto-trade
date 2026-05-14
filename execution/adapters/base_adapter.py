"""Base adapter for exchange connections."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class AccountBalance:
    total_equity: float
    available_balance: float
    locked_balance: float
    positions: Dict[str, Position]


class BaseAdapter(ABC):
    """Base class for exchange adapters."""

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        """
        Initialize exchange adapter.

        Args:
            api_key: Exchange API key
            api_secret: Exchange API secret
            testnet: Use testnet/simulation mode
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Connect to exchange."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from exchange."""
        pass

    @abstractmethod
    def get_balance(self) -> AccountBalance:
        """Get account balance."""
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol."""
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                    quantity: float, price: Optional[float] = None) -> Order:
        """Place an order."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str, symbol: str) -> OrderStatus:
        """Get order status."""
        pass

    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker/price."""
        pass

    def format_symbol(self, symbol: str) -> str:
        """Format symbol for exchange (e.g., BTC-USDT -> BTC/USDT)."""
        return symbol.replace("-", "/")

    def parse_symbol(self, symbol: str) -> str:
        """Parse exchange symbol to standard format (e.g., BTC/USDT -> BTC-USDT)."""
        return symbol.replace("/", "-")
