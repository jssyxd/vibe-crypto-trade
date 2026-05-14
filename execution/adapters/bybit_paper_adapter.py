"""
Bybit Paper Trading Adapter using CCXT.

Provides simulated trading on Bybit testnet with real-time position
tracking and PnL calculation. No real money is involved.
"""

import ccxt
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field

from .base_adapter import (
    BaseAdapter, Order, OrderSide, OrderType, OrderStatus,
    Position, AccountBalance
)


@dataclass
class PaperPosition:
    """In-memory position for paper trading."""
    symbol: str
    quantity: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    realized_pnl: float = 0.0
    side: str = "long"  # "long" or "short"

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized PnL."""
        if self.side == "long":
            return (self.current_price - self.entry_price) * self.quantity
        else:  # short
            return (self.entry_price - self.current_price) * self.quantity


@dataclass
class PaperOrder:
    """In-memory order tracking for paper trading."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    def to_order(self) -> Order:
        """Convert to base Order dataclass."""
        return Order(
            order_id=self.order_id,
            symbol=self.symbol,
            side=self.side,
            order_type=self.order_type,
            quantity=self.quantity,
            price=self.price,
            status=self.status,
            filled_qty=self.filled_qty,
            avg_fill_price=self.avg_fill_price,
            created_at=self.created_at,
            updated_at=self.updated_at,
            error=self.error,
        )


class BybitPaperAdapter(BaseAdapter):
    """
    Bybit paper trading adapter for testnet simulation.

    Features:
    - Connects to Bybit testnet via CCXT
    - Places simulated orders (no real money)
    - Tracks positions in memory
    - Calculates PnL in real-time
    - Graceful fallback to simulation mode if testnet unavailable
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
        initial_balance: float = 100000.0,
    ):
        """
        Initialize Bybit paper trading adapter.

        Args:
            api_key: Bybit API key (optional for simulation)
            api_secret: Bybit API secret (optional for simulation)
            testnet: Use Bybit testnet (default True)
            initial_balance: Starting paper trading balance
        """
        super().__init__(api_key, api_secret, testnet)
        self.initial_balance = initial_balance

        # Initialize CCXT exchange
        self.exchange = ccxt.bybit({
            'apiKey': api_key or 'paper_trading',
            'secret': api_secret or 'paper_trading',
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'testnet': testnet,
            },
        })

        # In-memory state
        self._balance = initial_balance
        self._locked_balance = 0.0
        self._positions: Dict[str, PaperPosition] = {}
        self._orders: Dict[str, PaperOrder] = {}
        self._order_counter = 0

        # Connection state
        self._use_simulation = False
        self._ws_connected = False

        # Callbacks for real-time updates
        self._position_callbacks: List[Callable[[str, PaperPosition], None]] = []
        self._order_callbacks: List[Callable[[str, PaperOrder], None]] = []

    def connect(self) -> bool:
        """
        Connect to Bybit testnet.

        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # Test connection to Bybit
            if self.testnet:
                self.exchange.set_sandbox_mode(True)

            # Try to fetch ticker to verify connection
            self.exchange.fetch_ticker('BTC/USDT')
            self.connected = True
            self._use_simulation = False
            return True
        except Exception as e:
            print(f"Bybit testnet connection failed: {e}")
            print("Using simulation mode for paper trading")
            self._use_simulation = True
            self.connected = True
            return True

    def disconnect(self) -> bool:
        """Disconnect from Bybit."""
        self.connected = False
        self._ws_connected = False
        return True

    def get_balance(self) -> AccountBalance:
        """
        Get current account balance.

        Returns:
            AccountBalance: Current balance and positions
        """
        positions = {}
        total_position_value = 0.0
        for symbol, pos in self._positions.items():
            if pos.quantity > 0:
                pos_value = pos.quantity * pos.current_price
                total_position_value += pos_value
                positions[symbol] = Position(
                    symbol=symbol,
                    quantity=pos.quantity,
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    unrealized_pnl=pos.unrealized_pnl,
                    realized_pnl=pos.realized_pnl,
                )

        return AccountBalance(
            total_equity=self._balance + total_position_value,
            available_balance=self._balance,
            locked_balance=self._locked_balance,
            positions=positions,
        )

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for symbol.

        Args:
            symbol: Trading symbol (e.g., BTC-USDT)

        Returns:
            Optional[Position]: Position if exists, None otherwise
        """
        if symbol in self._positions:
            pos = self._positions[symbol]
            if pos.quantity > 0:
                return Position(
                    symbol=symbol,
                    quantity=pos.quantity,
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    unrealized_pnl=pos.unrealized_pnl,
                    realized_pnl=pos.realized_pnl,
                )
        return None

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
    ) -> Order:
        """
        Place a simulated order.

        Args:
            symbol: Trading symbol (e.g., BTC-USDT)
            side: Order side (BUY or SELL)
            order_type: Order type (MARKET, LIMIT, STOP)
            quantity: Order quantity
            price: Limit price (None for market orders)

        Returns:
            Order: Placed order with fill information
        """
        self._order_counter += 1
        order_id = f"PAPER_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._order_counter}"

        # Get current market price
        ticker = self.get_ticker(symbol)
        current_price = ticker.get('last', 0) or ticker.get('ask', 0)

        # Determine fill price
        if order_type == OrderType.MARKET:
            fill_price = current_price
        else:
            fill_price = price or current_price

        # Create paper order
        paper_order = PaperOrder(
            order_id=order_id,
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

        # Store order
        self._orders[order_id] = paper_order

        # Execute the trade
        self._execute_trade(symbol, side, quantity, fill_price)

        # Notify callbacks
        for cb in self._order_callbacks:
            cb(order_id, paper_order)

        return paper_order.to_order()

    def _execute_trade(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        fill_price: float,
    ) -> None:
        """
        Execute a trade and update positions/balance.

        Args:
            symbol: Trading symbol
            side: Order side
            quantity: Order quantity
            fill_price: Execution price
        """
        base = symbol.split('-')[0]
        quote = symbol.split('-')[1]

        if symbol not in self._positions:
            self._positions[symbol] = PaperPosition(
                symbol=symbol,
                quantity=0.0,
                entry_price=0.0,
                current_price=fill_price,
            )

        pos = self._positions[symbol]

        if side == OrderSide.BUY:
            # Buying: deduct quote currency, add base currency
            cost = quantity * fill_price
            if cost > self._balance:
                # Insufficient balance - reject
                raise ValueError(f"Insufficient balance: required {cost}, available {self._balance}")

            self._balance -= cost

            # Update position
            if pos.quantity == 0:
                pos.entry_price = fill_price
                pos.side = "long"
                pos.quantity = quantity
            else:
                # Average in
                total_cost = pos.entry_price * pos.quantity + fill_price * quantity
                pos.quantity += quantity
                pos.entry_price = total_cost / pos.quantity

            pos.current_price = fill_price

        else:  # SELL
            # Selling: deduct base currency, add quote currency
            if quantity > pos.quantity:
                raise ValueError(f"Insufficient position: required {quantity}, available {pos.quantity}")

            proceeds = quantity * fill_price
            self._balance += proceeds

            # Calculate realized PnL for the sold portion
            if pos.side == "long":
                realized = (fill_price - pos.entry_price) * quantity
            else:  # short
                realized = (pos.entry_price - fill_price) * quantity

            pos.realized_pnl += realized
            pos.quantity -= quantity

            # Update position
            if pos.quantity > 0 and pos.side == "long":
                # Average remaining position
                pos.entry_price = fill_price
            pos.current_price = fill_price

        # Notify position callbacks
        for cb in self._position_callbacks:
            cb(symbol, pos)

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel
            symbol: Trading symbol

        Returns:
            bool: True if cancelled, False otherwise
        """
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now()
                return True
        return False

    def get_order_status(self, order_id: str, symbol: str) -> OrderStatus:
        """
        Get order status.

        Args:
            order_id: Order ID
            symbol: Trading symbol

        Returns:
            OrderStatus: Current order status
        """
        if order_id in self._orders:
            return self._orders[order_id].status
        return OrderStatus.REJECTED

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker/price for symbol.

        Args:
            symbol: Trading symbol (e.g., BTC-USDT)

        Returns:
            Dict containing ticker data
        """
        # Try to get real price from testnet
        if not self._use_simulation:
            try:
                ccxt_symbol = symbol.replace('-', '/')
                ticker = self.exchange.fetch_ticker(ccxt_symbol)
                return {
                    'symbol': symbol,
                    'last': ticker.get('last'),
                    'bid': ticker.get('bid'),
                    'ask': ticker.get('ask'),
                    'volume': ticker.get('baseVolume'),
                    'timestamp': datetime.now().isoformat(),
                }
            except Exception as e:
                print(f"Error fetching ticker: {e}")

        # Fall back to simulation prices
        return self._get_simulated_ticker(symbol)

    def _get_simulated_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get simulated ticker data."""
        # Use base prices for simulation
        base_prices = {
            'BTC-USDT': 80000.0,
            'ETH-USDT': 3000.0,
            'SOL-USDT': 150.0,
        }
        base_price = base_prices.get(symbol, 100.0)

        return {
            'symbol': symbol,
            'last': base_price,
            'bid': base_price - 10,
            'ask': base_price + 10,
            'volume': 1000000.0,
            'timestamp': datetime.now().isoformat(),
        }

    def update_prices(self, prices: Dict[str, float]) -> None:
        """
        Update current prices for all positions.

        Args:
            prices: Dict mapping symbol to current price
        """
        for symbol, price in prices.items():
            if symbol in self._positions:
                self._positions[symbol].current_price = price

                # Notify callbacks
                for cb in self._position_callbacks:
                    cb(symbol, self._positions[symbol])

    def get_pnl_summary(self) -> Dict[str, Any]:
        """
        Get PnL summary for all positions.

        Returns:
            Dict containing total unrealized and realized PnL
        """
        total_unrealized = 0.0
        total_realized = 0.0

        for pos in self._positions.values():
            total_unrealized += pos.unrealized_pnl
            total_realized += pos.realized_pnl

        return {
            'total_unrealized_pnl': total_unrealized,
            'total_realized_pnl': total_realized,
            'total_pnl': total_unrealized + total_realized,
            'positions': {
                symbol: {
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'realized_pnl': pos.realized_pnl,
                    'side': pos.side,
                }
                for symbol, pos in self._positions.items()
                if pos.quantity > 0
            },
        }

    def on_position_update(self, callback: Callable[[str, PaperPosition], None]) -> None:
        """Register callback for position updates."""
        self._position_callbacks.append(callback)

    def on_order_update(self, callback: Callable[[str, PaperOrder], None]) -> None:
        """Register callback for order updates."""
        self._order_callbacks.append(callback)

    def get_orders(self) -> List[Order]:
        """Get all orders."""
        return [order.to_order() for order in self._orders.values()]

    def get_open_orders(self) -> List[Order]:
        """Get all open (pending) orders."""
        return [
            order.to_order()
            for order in self._orders.values()
            if order.status == OrderStatus.PENDING
        ]

    def get_filled_orders(self) -> List[Order]:
        """Get all filled orders."""
        return [
            order.to_order()
            for order in self._orders.values()
            if order.status == OrderStatus.FILLED
        ]

    def reset(self, initial_balance: Optional[float] = None) -> None:
        """
        Reset paper trading account to initial state.

        Args:
            initial_balance: New initial balance (optional)
        """
        if initial_balance is not None:
            self.initial_balance = initial_balance

        self._balance = self.initial_balance
        self._locked_balance = 0.0
        self._positions.clear()
        self._orders.clear()
        self._order_counter = 0

    @property
    def total_equity(self) -> float:
        """Get total equity including unrealized PnL and position values."""
        position_value = sum(
            pos.quantity * pos.current_price
            for pos in self._positions.values()
        )
        return self._balance + position_value

    def get_portfolio_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio statistics.

        Returns:
            Dict with portfolio stats
        """
        pnl = self.get_pnl_summary()
        return {
            'total_equity': self.total_equity,
            'cash': self._balance,
            'locked_balance': self._locked_balance,
            'total_unrealized_pnl': pnl['total_unrealized_pnl'],
            'total_realized_pnl': pnl['total_realized_pnl'],
            'total_pnl': pnl['total_pnl'],
            'positions': pnl['positions'],
        }