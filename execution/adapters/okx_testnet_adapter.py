"""
OKX Testnet Adapter using CCXT.

Provides simulated trading on OKX testnet with real-time position
tracking and PnL calculation. No real money is involved.
"""

import ccxt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field

from .base_adapter import (
    BaseAdapter, Order, OrderSide, OrderType, OrderStatus,
    Position, AccountBalance
)


@dataclass
class TestnetPosition:
    """In-memory position for testnet trading."""
    symbol: str
    quantity: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    realized_pnl: float = 0.0
    side: str = "long"  # "long" or "short"
    avg_fill_price: float = 0.0  # Track average fill price for PnL

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized PnL."""
        if self.quantity == 0:
            return 0.0
        if self.side == "long":
            return (self.current_price - self.entry_price) * self.quantity
        else:  # short
            return (self.entry_price - self.current_price) * self.quantity


@dataclass
class TestnetOrder:
    """In-memory order tracking for testnet trading."""
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


@dataclass
class Trade:
    """Represents a filled trade/execution."""
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    price: float
    quantity: float
    quote_quantity: float
    fee: float = 0.0
    fee_currency: str = "USDT"
    timestamp: datetime = field(default_factory=datetime.now)


class OKXTestnetAdapter(BaseAdapter):
    """
    OKX testnet paper trading adapter.

    Features:
    - Connects to OKX testnet via CCXT
    - Places simulated orders (no real money)
    - Tracks positions in memory
    - Calculates PnL in real-time
    - Fetches order history and fills
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
        Initialize OKX testnet adapter.

        Args:
            api_key: OKX API key (optional for simulation)
            api_secret: OKX API secret (optional for simulation)
            testnet: Use OKX testnet (default True)
            initial_balance: Starting paper trading balance
        """
        super().__init__(api_key, api_secret, testnet)
        self.initial_balance = initial_balance

        # Initialize CCXT OKX exchange
        # OKX testnet is accessed via sandbox mode in CCXT
        self.exchange = ccxt.okx({
            'apiKey': api_key or 'testnet_key',
            'secret': api_secret or 'testnet_secret',
            'password': '',  # OKX requires passphrase
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'testnet': testnet,
            },
        })

        # In-memory state
        self._balance = initial_balance
        self._locked_balance = 0.0
        self._positions: Dict[str, TestnetPosition] = {}
        self._orders: Dict[str, TestnetOrder] = {}
        self._trades: Dict[str, List[Trade]] = {}  # order_id -> list of trades
        self._order_counter = 0
        self._trade_counter = 0

        # Connection state
        self._use_simulation = False
        self._testnet_available = False

        # Callbacks for real-time updates
        self._position_callbacks: List[Callable[[str, TestnetPosition], None]] = []
        self._order_callbacks: List[Callable[[str, TestnetOrder], None]] = []

    def connect(self) -> bool:
        """
        Connect to OKX testnet.

        Returns:
            bool: True if connected, False otherwise
        """
        if not self.testnet:
            # Production mode - require real credentials
            if not self.api_key or not self.api_secret:
                print("Production mode requires API key and secret")
                self._use_simulation = True
                self.connected = True
                return True

        try:
            # Try to enable sandbox/testnet mode
            if hasattr(self.exchange, 'set_sandbox_mode'):
                self.exchange.set_sandbox_mode(self.testnet)

            # Test connection by fetching ticker
            self.exchange.fetch_ticker('BTC/USDT')
            self.connected = True
            self._use_simulation = False
            self._testnet_available = True
            return True
        except Exception as e:
            print(f"OKX testnet connection failed: {e}")
            print("Using simulation mode for paper trading")
            self._use_simulation = True
            self._testnet_available = False
            self.connected = True
            return True

    def disconnect(self) -> bool:
        """Disconnect from OKX."""
        self.connected = False
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
            if pos.quantity != 0:
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
            if pos.quantity != 0:
                return Position(
                    symbol=symbol,
                    quantity=pos.quantity,
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    unrealized_pnl=pos.unrealized_pnl,
                    realized_pnl=pos.realized_pnl,
                )
        return None

    def validate_position(self, symbol: str) -> Dict[str, Any]:
        """
        Validate position against exchange (simulation).

        Args:
            symbol: Trading symbol to validate

        Returns:
            Dict with validation results
        """
        local_pos = self.get_position(symbol)
        if local_pos is None:
            return {
                'valid': True,
                'symbol': symbol,
                'local_quantity': 0.0,
                'exchange_quantity': 0.0,
                'match': True,
            }

        # In simulation mode, exchange quantity matches local
        return {
            'valid': True,
            'symbol': symbol,
            'local_quantity': local_pos.quantity,
            'exchange_quantity': local_pos.quantity,
            'match': True,
            'pnl': local_pos.unrealized_pnl,
        }

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
        order_id = f"OKX_TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._order_counter}"

        # Get current market price
        ticker = self.get_ticker(symbol)
        current_price = ticker.get('last', 0) or ticker.get('ask', 0)

        # Determine fill price
        if order_type == OrderType.MARKET:
            fill_price = current_price
        else:
            fill_price = price or current_price

        # Create testnet order
        testnet_order = TestnetOrder(
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
        self._orders[order_id] = testnet_order

        # Execute the trade
        trade = self._execute_trade(symbol, side, quantity, fill_price)

        # Track trade for order
        self._trades[order_id] = [trade]

        # Notify callbacks
        for cb in self._order_callbacks:
            cb(order_id, testnet_order)

        return testnet_order.to_order()

    def _execute_trade(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        fill_price: float,
    ) -> Trade:
        """
        Execute a trade and update positions/balance.

        Args:
            symbol: Trading symbol
            side: Order side
            quantity: Order quantity
            fill_price: Execution price

        Returns:
            Trade: The executed trade
        """
        self._trade_counter += 1
        trade_id = f"OKX_TRADE_{self._trade_counter}"

        base = symbol.split('-')[0]
        quote = symbol.split('-')[1]
        quote_quantity = quantity * fill_price

        # Create trade record
        trade = Trade(
            trade_id=trade_id,
            order_id="",  # Will be set by caller
            symbol=symbol,
            side=side,
            price=fill_price,
            quantity=quantity,
            quote_quantity=quote_quantity,
            fee=quote_quantity * 0.001,  # 0.1% fee
            fee_currency=quote,
        )

        if symbol not in self._positions:
            self._positions[symbol] = TestnetPosition(
                symbol=symbol,
                quantity=0.0,
                entry_price=0.0,
                current_price=fill_price,
            )

        pos = self._positions[symbol]

        if side == OrderSide.BUY:
            # Buying: deduct quote currency, add base currency
            if quote_quantity > self._balance:
                raise ValueError(f"Insufficient balance: required {quote_quantity}, available {self._balance}")

            self._balance -= quote_quantity

            # Update position
            if pos.quantity == 0:
                pos.entry_price = fill_price
                pos.avg_fill_price = fill_price
                pos.side = "long"
                pos.quantity = quantity
            else:
                # Average in - calculate new average fill price
                total_cost = (pos.avg_fill_price * pos.quantity) + (fill_price * quantity)
                new_quantity = pos.quantity + quantity
                pos.avg_fill_price = total_cost / new_quantity
                pos.quantity = new_quantity
                pos.entry_price = pos.avg_fill_price

            pos.current_price = fill_price

        else:  # SELL
            # Selling: deduct base currency, add quote currency
            if quantity > pos.quantity:
                raise ValueError(f"Insufficient position: required {quantity}, available {pos.quantity}")

            proceeds = quote_quantity
            self._balance += proceeds

            # Calculate realized PnL for the sold portion
            if pos.side == "long":
                realized = (fill_price - pos.avg_fill_price) * quantity
            else:  # short
                realized = (pos.avg_fill_price - fill_price) * quantity

            pos.realized_pnl += realized
            pos.quantity -= quantity

            # Update current price
            pos.current_price = fill_price

            # If position closed, record final PnL
            if pos.quantity == 0:
                pos.entry_price = 0.0
                pos.avg_fill_price = 0.0

        # Notify position callbacks
        for cb in self._position_callbacks:
            cb(symbol, pos)

        return trade

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

    def get_order_history(
        self,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> List[Order]:
        """
        Get order history.

        Args:
            symbol: Filter by symbol (optional)
            status: Filter by status (optional)
            limit: Maximum number of orders to return

        Returns:
            List of Order objects
        """
        orders = list(self._orders.values())

        # Filter by symbol
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]

        # Filter by status
        if status:
            orders = [o for o in orders if o.status == status]

        # Sort by created_at descending and limit
        orders.sort(key=lambda x: x.created_at, reverse=True)
        orders = orders[:limit]

        return [o.to_order() for o in orders]

    def get_fills(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get fills/trades history.

        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum number of fills to return

        Returns:
            List of trade dictionaries
        """
        all_trades = []
        for order_trades in self._trades.values():
            all_trades.extend(order_trades)

        # Filter by symbol
        if symbol:
            all_trades = [t for t in all_trades if t.symbol == symbol]

        # Sort by timestamp descending and limit
        all_trades.sort(key=lambda x: x.timestamp, reverse=True)
        all_trades = all_trades[:limit]

        return [
            {
                'trade_id': t.trade_id,
                'order_id': t.order_id,
                'symbol': t.symbol,
                'side': t.side.value,
                'price': t.price,
                'quantity': t.quantity,
                'quote_quantity': t.quote_quantity,
                'fee': t.fee,
                'fee_currency': t.fee_currency,
                'timestamp': t.timestamp.isoformat(),
            }
            for t in all_trades
        ]

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker/price for symbol.

        Args:
            symbol: Trading symbol (e.g., BTC-USDT)

        Returns:
            Dict containing ticker data
        """
        # Try to get real price from testnet
        if not self._use_simulation and self._testnet_available:
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
                if pos.quantity != 0
            },
        }

    def on_position_update(self, callback: Callable[[str, TestnetPosition], None]) -> None:
        """Register callback for position updates."""
        self._position_callbacks.append(callback)

    def on_order_update(self, callback: Callable[[str, TestnetOrder], None]) -> None:
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
        self._trades.clear()
        self._order_counter = 0
        self._trade_counter = 0

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

    @property
    def is_simulation_mode(self) -> bool:
        """Check if running in simulation mode."""
        return self._use_simulation

    @property
    def is_testnet_available(self) -> bool:
        """Check if testnet was successfully connected."""
        return self._testnet_available