"""Bybit exchange adapter using CCXT."""

import ccxt
from datetime import datetime
from typing import Optional, Dict, Any

from .base_adapter import (
    BaseAdapter, Order, OrderSide, OrderType, OrderStatus,
    Position, AccountBalance
)


class BybitAdapter(BaseAdapter):
    """Bybit exchange adapter."""

    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        """
        Initialize Bybit adapter.

        Args:
            api_key: Bybit API key (optional for simulation)
            api_secret: Bybit API secret (optional for simulation)
            testnet: Use Bybit testnet (default True)
        """
        super().__init__(api_key, api_secret, testnet)

        # Initialize CCXT Bybit
        self.exchange = ccxt.bybit({
            'apiKey': api_key or 'simulation',
            'secret': api_secret or 'simulation',
            'testnet': testnet,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # or 'linear' for USDT perpetual
            },
        })

        # For simulation, use mock balance
        self._mock_balance = {
            'USDT': {
                'free': 100000.0,
                'locked': 0.0,
            },
            'BTC': {
                'free': 0.0,
                'locked': 0.0,
            },
        }
        self._mock_positions = {}

    def connect(self) -> bool:
        """Connect to Bybit."""
        try:
            # For simulation, just mark as connected
            if not self.api_key or self.api_key == 'simulation':
                self.connected = True
                return True

            # Test API connection
            self.exchange.fetch_balance()
            self.connected = True
            return True
        except Exception as e:
            print(f"Bybit connection error: {e}")
            self.connected = False
            return False

    def disconnect(self) -> bool:
        """Disconnect from Bybit."""
        self.connected = False
        return True

    def get_balance(self) -> AccountBalance:
        """Get account balance."""
        total_equity = sum(v['free'] + v['locked'] for v in self._mock_balance.values())

        positions = {}
        for symbol, pos in self._mock_positions.items():
            positions[symbol] = Position(
                symbol=symbol,
                quantity=pos['qty'],
                entry_price=pos['entry'],
                current_price=pos.get('current', pos['entry']),
                unrealized_pnl=pos.get('pnl', 0.0),
            )

        return AccountBalance(
            total_equity=total_equity,
            available_balance=self._mock_balance.get('USDT', {}).get('free', 0.0),
            locked_balance=sum(v['locked'] for v in self._mock_balance.values()),
            positions=positions,
        )

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol."""
        if symbol in self._mock_positions:
            pos = self._mock_positions[symbol]
            return Position(
                symbol=symbol,
                quantity=pos['qty'],
                entry_price=pos['entry'],
                current_price=pos.get('current', pos['entry']),
                unrealized_pnl=pos.get('pnl', 0.0),
            )
        return None

    def place_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                    quantity: float, price: Optional[float] = None) -> Order:
        """Place an order (simulation)."""
        order_id = f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S')}_{symbol}"

        # Simulate order fill at current price
        ticker = self.get_ticker(symbol)
        fill_price = price or ticker.get('last', ticker.get('ask', 0))

        order = Order(
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

        # Update mock balance and positions
        base = symbol.split('-')[0]
        quote = symbol.split('-')[1]

        if side == OrderSide.BUY:
            cost = quantity * fill_price
            self._mock_balance[quote]['free'] -= cost
            self._mock_balance[base]['free'] += quantity
        else:
            cost = quantity * fill_price
            self._mock_balance[base]['free'] -= quantity
            self._mock_balance[quote]['free'] += cost

        # Update position
        self._mock_positions[symbol] = {
            'qty': self._mock_balance[base]['free'],
            'entry': fill_price,
            'current': fill_price,
            'pnl': 0.0,
        }

        return order

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order (simulation - no-op)."""
        return True

    def get_order_status(self, order_id: str, symbol: str) -> OrderStatus:
        """Get order status."""
        return OrderStatus.FILLED

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker/price from OKX or mock."""
        # Try to get real price from OKX via CCXT
        try:
            okx = ccxt.okx({'enableRateLimit': True})
            ticker = okx.fetch_ticker(symbol.replace('-', '/'))
            return ticker
        except Exception as e:
            # Fall back to mock price
            return {
                'symbol': symbol,
                'last': 80000.0,  # Mock BTC price
                'bid': 79990.0,
                'ask': 80010.0,
                'volume': 1000000,
            }
