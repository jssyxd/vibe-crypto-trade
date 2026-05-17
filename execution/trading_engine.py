"""
E2E Trading Engine - End-to-end signal processing, order routing, fill handling, position updates.

Coordinates multiple exchange adapters, processes signals from multiple strategies,
routes orders to appropriate exchanges, handles fills, and updates positions in real-time.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List, Any, Callable, Set
from enum import Enum
import uuid

from execution.adapters import BybitPaperAdapter, OKXTestnetAdapter, BaseAdapter
from execution.adapters.base_adapter import (
    Order, OrderSide, OrderType, OrderStatus, Position, AccountBalance
)
from execution.risk.live_risk_guard import LiveRiskGuard, LiveRiskConfig, PreTradeCheckResult
from execution.signals.signal_queue import SignalQueue, TradingSignal, SignalPriority


class Exchange(Enum):
    """Supported exchanges."""
    BYBIT = "bybit"
    OKX = "okx"


@dataclass
class FillEvent:
    """Represents a filled order event."""
    fill_id: str
    order_id: str
    signal_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    exchange: Exchange
    timestamp: datetime
    commission: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class PositionUpdate:
    """Represents a position update."""
    symbol: str
    exchange: Exchange
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    side: str  # "long" or "short"
    timestamp: datetime


@dataclass
class OrderRequest:
    """Internal order request representation."""
    signal_id: str
    symbol: str
    side: str  # "buy" or "sell"
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    exchange: Optional[Exchange] = None
    strategy_name: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class OrderResult:
    """Result of order submission."""
    success: bool
    order_id: Optional[str] = None
    signal_id: Optional[str] = None
    symbol: str = ""
    exchange: Optional[Exchange] = None
    status: str = ""  # pending, filled, partial, rejected, error
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    message: str = ""
    fill_events: List[FillEvent] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class TradingEngine:
    """
    E2E Trading Engine that orchestrates the complete trading workflow.

    Features:
    - Signal processing from multiple strategies
    - Order routing to appropriate exchanges
    - Fill handling and position updates
    - Real-time risk validation via LiveRiskGuard
    - Portfolio value tracking
    - Multi-exchange support (Bybit, OKX)
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        risk_config: Optional[LiveRiskConfig] = None,
    ):
        """
        Initialize E2E Trading Engine.

        Args:
            config: Trading engine configuration
            risk_config: Risk guard configuration
        """
        self.config = config or {}
        self._lock = threading.RLock()

        # Initialize adapters for each exchange
        self._adapters: Dict[Exchange, BaseAdapter] = {}
        self._adapter_configs: Dict[Exchange, Dict] = {}

        # Initialize risk guard
        self.risk_guard = LiveRiskGuard(risk_config or LiveRiskConfig())

        # Initialize signal queue
        self.signal_queue = SignalQueue()

        # Internal state
        self._positions: Dict[str, Dict[str, Position]] = {}  # exchange -> symbol -> Position
        self._orders: Dict[str, OrderResult] = {}  # order_id -> OrderResult
        self._signal_to_order: Dict[str, str] = {}  # signal_id -> order_id

        # Portfolio tracking
        self._portfolio_value = 100000.0
        self._initial_capital = self._portfolio_value

        # Callbacks for events
        self._on_fill_callbacks: List[Callable[[FillEvent], None]] = []
        self._on_position_update_callbacks: List[Callable[[PositionUpdate], None]] = []
        self._on_order_callbacks: List[Callable[[OrderResult], None]] = []

        # Statistics
        self._stats = {
            'signals_processed': 0,
            'signals_rejected': 0,
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_failed': 0,
            'total_commission': 0.0,
            'total_realized_pnl': 0.0,
        }

    def register_adapter(self, exchange: Exchange, adapter: BaseAdapter) -> None:
        """
        Register an exchange adapter.

        Args:
            exchange: Exchange identifier
            adapter: Exchange adapter instance
        """
        with self._lock:
            self._adapters[exchange] = adapter
            self._positions[str(exchange.value)] = {}

    def add_adapter_config(self, exchange: Exchange, config: Dict[str, Any]) -> None:
        """
        Add configuration for an exchange adapter.

        Args:
            exchange: Exchange identifier
            config: Adapter configuration (api_key, api_secret, testnet, etc.)
        """
        self._adapter_configs[exchange] = config

    def initialize_adapters(self) -> Dict[str, bool]:
        """
        Initialize all configured adapters.

        Returns:
            Dict mapping exchange name to connection status
        """
        results = {}

        for exchange, config in self._adapter_configs.items():
            try:
                if exchange == Exchange.BYBIT:
                    adapter = BybitPaperAdapter(
                        api_key=config.get('api_key', ''),
                        api_secret=config.get('api_secret', ''),
                        testnet=config.get('testnet', True),
                        initial_balance=config.get('initial_balance', 100000.0),
                    )
                elif exchange == Exchange.OKX:
                    adapter = OKXTestnetAdapter(
                        api_key=config.get('api_key', ''),
                        api_secret=config.get('api_secret', ''),
                        testnet=config.get('testnet', True),
                        initial_balance=config.get('initial_balance', 100000.0),
                    )
                else:
                    continue

                adapter.connect()
                self.register_adapter(exchange, adapter)
                results[str(exchange.value)] = True

            except Exception as e:
                print(f"Failed to initialize {exchange.value}: {e}")
                results[str(exchange.value)] = False

        return results

    # ==================== Signal Processing ====================

    def validate_signal(self, signal: TradingSignal) -> tuple[bool, str]:
        """
        Validate signal format and required fields.

        Args:
            signal: Trading signal to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not signal.signal_id:
            return False, "Missing signal_id"

        if not signal.symbol:
            return False, "Missing symbol"

        if signal.side.lower() not in ['buy', 'sell']:
            return False, f"Invalid side: {signal.side}"

        if signal.quantity <= 0:
            return False, f"Invalid quantity: {signal.quantity}"

        if signal.price is not None and signal.price <= 0:
            return False, f"Invalid price: {signal.price}"

        return True, ""

    def submit_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """
        Submit a signal to the trading engine for processing.

        Args:
            signal: Trading signal to process

        Returns:
            Dict with submission status
        """
        with self._lock:
            # Validate signal
            is_valid, error_msg = self.validate_signal(signal)
            if not is_valid:
                return {
                    'success': False,
                    'signal_id': signal.signal_id,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat(),
                }

            # Add to signal queue
            self.signal_queue.add(signal)

            return {
                'success': True,
                'signal_id': signal.signal_id,
                'message': 'Signal queued for processing',
                'timestamp': datetime.now().isoformat(),
            }

    def process_signal(self, signal: TradingSignal) -> OrderResult:
        """
        Process a trading signal through the full workflow.

        Args:
            signal: Trading signal to process

        Returns:
            OrderResult with execution details
        """
        with self._lock:
            self._stats['signals_processed'] += 1

            # Validate signal
            is_valid, error_msg = self.validate_signal(signal)
            if not is_valid:
                self._stats['signals_rejected'] += 1
                return OrderResult(
                    success=False,
                    signal_id=signal.signal_id,
                    symbol=signal.symbol,
                    status='rejected',
                    message=error_msg,
                )

            # Determine target exchange
            exchange = self._determine_exchange(signal)

            # Get adapter for exchange
            adapter = self._adapters.get(exchange)
            if not adapter:
                return OrderResult(
                    success=False,
                    signal_id=signal.signal_id,
                    symbol=signal.symbol,
                    exchange=exchange,
                    status='error',
                    message=f"No adapter registered for {exchange.value}",
                )

            # Get current price and portfolio value for risk check
            ticker = adapter.get_ticker(signal.symbol)
            current_price = ticker.get('last', 0) or ticker.get('ask', 0)
            if current_price == 0:
                current_price = signal.price or 0

            balance = adapter.get_balance()
            self._portfolio_value = balance.total_equity

            # Pre-trade risk check
            risk_result = self.risk_guard.check_pre_trade(
                symbol=signal.symbol,
                side=signal.side,
                quantity=signal.quantity,
                price=current_price,
            )

            if not risk_result.approved:
                self._stats['signals_rejected'] += 1
                return OrderResult(
                    success=False,
                    signal_id=signal.signal_id,
                    symbol=signal.symbol,
                    exchange=exchange,
                    status='rejected',
                    message=risk_result.message,
                )

            # Apply risk adjustments if any
            quantity = signal.quantity
            if risk_result.adjusted_quantity:
                quantity = risk_result.adjusted_quantity

            # Convert signal to order
            try:
                order = adapter.place_order(
                    symbol=signal.symbol,
                    side=OrderSide.BUY if signal.side.lower() == 'buy' else OrderSide.SELL,
                    order_type=OrderType.MARKET if not signal.price else OrderType.LIMIT,
                    quantity=quantity,
                    price=signal.price,
                )

                # Create order result
                result = OrderResult(
                    success=True,
                    order_id=order.order_id,
                    signal_id=signal.signal_id,
                    symbol=signal.symbol,
                    exchange=exchange,
                    status=order.status.value if order.status else 'pending',
                    filled_qty=order.filled_qty,
                    avg_fill_price=order.avg_fill_price,
                    message=f"Order {order.status.value}: {order.order_id}",
                )

                # Track order
                self._orders[order.order_id] = result
                self._signal_to_order[signal.signal_id] = order.order_id

                # Update stats
                if order.status == OrderStatus.FILLED:
                    self._stats['orders_filled'] += 1
                    self._stats['orders_placed'] += 1
                else:
                    self._stats['orders_placed'] += 1

                # Create fill event
                fill_event = FillEvent(
                    fill_id=str(uuid.uuid4()),
                    order_id=order.order_id,
                    signal_id=signal.signal_id,
                    symbol=signal.symbol,
                    side=OrderSide.BUY if signal.side.lower() == 'buy' else OrderSide.SELL,
                    quantity=order.filled_qty,
                    price=order.avg_fill_price,
                    exchange=exchange,
                    timestamp=datetime.now(),
                    commission=self._calculate_commission(order.filled_qty, order.avg_fill_price, exchange),
                )
                result.fill_events.append(fill_event)

                # Update position from fill
                self._update_position_from_fill(fill_event)

                # Record post-trade risk update
                self.risk_guard.record_post_trade(
                    symbol=signal.symbol,
                    side=signal.side,
                    quantity=order.filled_qty,
                    price=order.avg_fill_price,
                )

                # Notify callbacks
                for cb in self._on_fill_callbacks:
                    cb(fill_event)

                for cb in self._on_order_callbacks:
                    cb(result)

                return result

            except Exception as e:
                self._stats['orders_failed'] += 1
                return OrderResult(
                    success=False,
                    signal_id=signal.signal_id,
                    symbol=signal.symbol,
                    exchange=exchange,
                    status='error',
                    message=str(e),
                )

    def _determine_exchange(self, signal: TradingSignal) -> Exchange:
        """
        Determine target exchange based on signal metadata or round-robin.

        Args:
            signal: Trading signal

        Returns:
            Exchange identifier
        """
        # Check signal metadata for exchange preference
        if signal.metadata:
            exchange_name = signal.metadata.get('exchange', '').lower()
            if exchange_name == 'okx':
                return Exchange.OKX
            elif exchange_name == 'bybit':
                return Exchange.BYBIT

        # Check strategy name patterns
        if signal.strategy_name:
            if 'okx' in signal.strategy_name.lower():
                return Exchange.OKX
            elif 'bybit' in signal.strategy_name.lower():
                return Exchange.BYBIT

        # Default to first available exchange
        if self._adapters:
            return list(self._adapters.keys())[0]

        return Exchange.BYBIT

    def _calculate_commission(self, quantity: float, price: float, exchange: Exchange) -> float:
        """Calculate commission for a trade."""
        # Typical commission rates
        commission_rates = {
            Exchange.BYBIT: 0.0005,  # 0.05%
            Exchange.OKX: 0.001,  # 0.1%
        }
        rate = commission_rates.get(exchange, 0.001)
        commission = quantity * price * rate
        self._stats['total_commission'] += commission
        return commission

    # ==================== Order Routing ====================

    def route_order(self, order_request: OrderRequest) -> OrderResult:
        """
        Route an order to the appropriate exchange.

        Args:
            order_request: Order request to route

        Returns:
            OrderResult with execution details
        """
        with self._lock:
            # Determine exchange if not specified
            exchange = order_request.exchange or self._get_exchange_for_symbol(order_request.symbol)

            # Get adapter
            adapter = self._adapters.get(exchange)
            if not adapter:
                return OrderResult(
                    success=False,
                    signal_id=order_request.signal_id,
                    symbol=order_request.symbol,
                    status='error',
                    message=f"No adapter for exchange: {exchange}",
                )

            # Submit order
            try:
                order = adapter.place_order(
                    symbol=order_request.symbol,
                    side=order_request.side if isinstance(order_request.side, OrderSide) else (
                        OrderSide.BUY if order_request.side.lower() == 'buy' else OrderSide.SELL
                    ),
                    order_type=order_request.order_type,
                    quantity=order_request.quantity,
                    price=order_request.price,
                )

                result = OrderResult(
                    success=True,
                    order_id=order.order_id,
                    signal_id=order_request.signal_id,
                    symbol=order_request.symbol,
                    exchange=exchange,
                    status=order.status.value if order.status else 'pending',
                    filled_qty=order.filled_qty,
                    avg_fill_price=order.avg_fill_price,
                    message=f"Order routed to {exchange.value}",
                )

                self._orders[order.order_id] = result

                # Notify callbacks
                for cb in self._on_order_callbacks:
                    cb(result)

                return result

            except Exception as e:
                return OrderResult(
                    success=False,
                    signal_id=order_request.signal_id,
                    symbol=order_request.symbol,
                    exchange=exchange,
                    status='error',
                    message=str(e),
                )

    def _get_exchange_for_symbol(self, symbol: str) -> Exchange:
        """Get preferred exchange for a symbol."""
        # Check if symbol has existing position
        for exchange_str, positions in self._positions.items():
            if symbol in positions:
                return Exchange(exchange_str)

        # Default to first available
        if self._adapters:
            return list(self._adapters.keys())[0]

        return Exchange.BYBIT

    def cancel_order(self, order_id: str, symbol: str, exchange: Optional[Exchange] = None) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel
            symbol: Trading symbol
            exchange: Exchange (optional, uses first available if not specified)

        Returns:
            bool: True if cancelled successfully
        """
        with self._lock:
            if exchange is None:
                exchange = self._get_exchange_for_symbol(symbol)

            adapter = self._adapters.get(exchange)
            if not adapter:
                return False

            try:
                return adapter.cancel_order(order_id, symbol)
            except Exception:
                return False

    def get_order_status(self, order_id: str, symbol: str, exchange: Optional[Exchange] = None) -> Optional[OrderStatus]:
        """
        Get status of an order.

        Args:
            order_id: Order ID
            symbol: Trading symbol
            exchange: Exchange (optional)

        Returns:
            OrderStatus or None if not found
        """
        with self._lock:
            if exchange is None:
                exchange = self._get_exchange_for_symbol(symbol)

            adapter = self._adapters.get(exchange)
            if not adapter:
                return None

            return adapter.get_order_status(order_id, symbol)

    # ==================== Fill Handling ====================

    def _update_position_from_fill(self, fill: FillEvent) -> None:
        """
        Update position from fill event.

        Args:
            fill: Fill event to process
        """
        exchange_key = str(fill.exchange.value)

        if exchange_key not in self._positions:
            self._positions[exchange_key] = {}

        positions = self._positions[exchange_key]

        if fill.symbol not in positions:
            positions[fill.symbol] = Position(
                symbol=fill.symbol,
                quantity=0.0,
                entry_price=0.0,
                current_price=fill.price,
            )

        pos = positions[fill.symbol]

        if fill.side == OrderSide.BUY:
            # Add to position
            if pos.quantity == 0:
                pos.entry_price = fill.price
                pos.quantity = fill.quantity
            else:
                # Average in
                total_cost = (pos.entry_price * pos.quantity) + (fill.price * fill.quantity)
                pos.quantity += fill.quantity
                pos.entry_price = total_cost / pos.quantity
        else:
            # Remove from position
            if pos.quantity > 0:
                # Calculate realized PnL
                if pos.entry_price > 0:
                    fill.pnl = (fill.price - pos.entry_price) * fill.quantity
                    self._stats['total_realized_pnl'] += fill.pnl

                pos.quantity -= fill.quantity
                if pos.quantity > 0:
                    pos.entry_price = fill.price  # Average remaining

        pos.current_price = fill.price

        # Notify position callbacks
        pos_update = PositionUpdate(
            symbol=fill.symbol,
            exchange=fill.exchange,
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            current_price=pos.current_price,
            unrealized_pnl=(pos.current_price - pos.entry_price) * pos.quantity if pos.quantity > 0 else 0.0,
            realized_pnl=0.0,  # Would need accumulation
            side='long' if fill.side == OrderSide.BUY else 'short',
            timestamp=datetime.now(),
        )

        for cb in self._on_position_update_callbacks:
            cb(pos_update)

    def handle_fill(self, fill: FillEvent) -> None:
        """
        Handle a fill event from an exchange.

        Args:
            fill: Fill event to process
        """
        with self._lock:
            self._update_position_from_fill(fill)

            # Update risk guard
            self.risk_guard.record_trade_result(
                symbol=fill.symbol,
                side=fill.side.value if hasattr(fill.side, 'value') else str(fill.side),
                quantity=fill.quantity,
                price=fill.price,
                realized_pnl=fill.realized_pnl,
            )

            # Notify callbacks
            for cb in self._on_fill_callbacks:
                cb(fill)

    # ==================== Position Updates ====================

    def update_positions(self, prices: Optional[Dict[str, Dict[str, float]]] = None) -> None:
        """
        Update current prices for all positions.

        Args:
            prices: Dict mapping exchange -> symbol -> price
        """
        with self._lock:
            if prices is None:
                # Fetch current prices from adapters
                prices = {}
                for exchange, adapter in self._adapters.items():
                    exchange_key = str(exchange.value)
                    prices[exchange_key] = {}
                    for symbol in self._positions.get(exchange_key, {}):
                        ticker = adapter.get_ticker(symbol)
                        prices[exchange_key][symbol] = ticker.get('last', 0) or ticker.get('ask', 0)

            # Update position prices
            for exchange_key, symbol_prices in prices.items():
                if exchange_key not in self._positions:
                    continue

                for symbol, price in symbol_prices.items():
                    if symbol in self._positions[exchange_key]:
                        pos = self._positions[exchange_key][symbol]
                        pos.current_price = price

    def get_position(self, symbol: str, exchange: Optional[Exchange] = None) -> Optional[Position]:
        """
        Get position for a symbol.

        Args:
            symbol: Trading symbol
            exchange: Exchange (optional)

        Returns:
            Position or None if not found
        """
        with self._lock:
            if exchange is None:
                exchange = self._get_exchange_for_symbol(symbol)

            exchange_key = str(exchange.value)
            if exchange_key in self._positions:
                return self._positions[exchange_key].get(symbol)

            return None

    def get_all_positions(self) -> Dict[str, Dict[str, Position]]:
        """Get all positions across all exchanges."""
        with self._lock:
            return self._positions.copy()

    def update_portfolio_value(self, value: Optional[float] = None) -> float:
        """
        Update and return current portfolio value.

        Args:
            value: Optional explicit portfolio value

        Returns:
            Current portfolio value
        """
        with self._lock:
            if value is not None:
                self._portfolio_value = value
                self.risk_guard.update_portfolio_value(value)
            elif self._adapters:
                # Calculate from adapters
                total = 0.0
                for adapter in self._adapters.values():
                    balance = adapter.get_balance()
                    total += balance.total_equity
                self._portfolio_value = total
                self.risk_guard.update_portfolio_value(total)
            # else: keep current _portfolio_value

            return self._portfolio_value

    # ==================== Portfolio ====================

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary.

        Returns:
            Dict with portfolio statistics
        """
        with self._lock:
            total_equity = 0.0
            total_cash = 0.0
            total_unrealized_pnl = 0.0
            total_realized_pnl = self._stats['total_realized_pnl']

            positions_by_exchange = {}

            for exchange, adapter in self._adapters.items():
                balance = adapter.get_balance()
                total_equity += balance.total_equity
                total_cash += balance.available_balance

                # Get positions
                exchange_key = str(exchange.value)
                positions = self._positions.get(exchange_key, {})

                exchange_positions = {}
                for symbol, pos in positions.items():
                    if pos.quantity > 0:
                        unrealized = (pos.current_price - pos.entry_price) * pos.quantity
                        total_unrealized_pnl += unrealized
                        exchange_positions[symbol] = {
                            'quantity': pos.quantity,
                            'entry_price': pos.entry_price,
                            'current_price': pos.current_price,
                            'unrealized_pnl': unrealized,
                            'side': 'long' if pos.quantity > 0 else 'short',
                        }

                if exchange_positions:
                    positions_by_exchange[exchange.value] = exchange_positions

            return {
                'total_equity': total_equity,
                'initial_capital': self._initial_capital,
                'cash': total_cash,
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_realized_pnl': total_realized_pnl,
                'total_pnl': total_unrealized_pnl + total_realized_pnl,
                'pnl_pct': ((total_equity - self._initial_capital) / self._initial_capital * 100) if self._initial_capital > 0 else 0.0,
                'positions': positions_by_exchange,
                'portfolio_value': self._portfolio_value,
                'risk_status': self.risk_guard.get_risk_status(),
            }

    # ==================== Risk ====================

    def check_risk(self, symbol: str, side: str, quantity: float, price: float) -> PreTradeCheckResult:
        """
        Perform pre-trade risk check.

        Args:
            symbol: Trading symbol
            side: Order side
            quantity: Order quantity
            price: Order price

        Returns:
            PreTradeCheckResult with approval status
        """
        return self.risk_guard.check_pre_trade(symbol, side, quantity, price)

    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status."""
        return self.risk_guard.get_risk_status()

    # ==================== Callbacks ====================

    def on_fill(self, callback: Callable[[FillEvent], None]) -> None:
        """Register callback for fill events."""
        self._on_fill_callbacks.append(callback)

    def on_position_update(self, callback: Callable[[PositionUpdate], None]) -> None:
        """Register callback for position updates."""
        self._on_position_update_callbacks.append(callback)

    def on_order(self, callback: Callable[[OrderResult], None]) -> None:
        """Register callback for order results."""
        self._on_order_callbacks.append(callback)

    # ==================== Statistics ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get trading engine statistics."""
        with self._lock:
            return {
                **self._stats,
                'signal_queue_stats': self.signal_queue.get_stats(),
                'open_orders': len([o for o in self._orders.values() if o.status == 'pending']),
                'filled_orders': len([o for o in self._orders.values() if o.status == 'filled']),
            }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._stats = {
                'signals_processed': 0,
                'signals_rejected': 0,
                'orders_placed': 0,
                'orders_filled': 0,
                'orders_failed': 0,
                'total_commission': 0.0,
                'total_realized_pnl': 0.0,
            }

    # ==================== Signal Queue Integration ====================

    def process_pending_signals(self, max_signals: int = 10) -> Dict[str, Any]:
        """
        Process pending signals from the signal queue.

        Args:
            max_signals: Maximum number of signals to process

        Returns:
            Dict with processing results
        """
        results = []
        processed = 0
        rejected = 0
        failed = 0

        for _ in range(max_signals):
            signal = self.signal_queue.get_next()
            if not signal:
                break

            result = self.process_signal(signal)
            results.append({
                'signal_id': signal.signal_id,
                'success': result.success,
                'status': result.status,
                'order_id': result.order_id,
            })

            if result.success:
                processed += 1
            elif result.status == 'rejected':
                rejected += 1
            else:
                failed += 1

        return {
            'processed': processed,
            'rejected': rejected,
            'failed': failed,
            'results': results,
        }

    def clear_processed_signals(self, before_hours: int = 24) -> None:
        """Clear processed signals older than specified hours."""
        self.signal_queue.clear_processed(before_hours=before_hours)

    # ==================== Exchange Access (for API) ====================

    @property
    def adapters(self) -> Dict[str, BaseAdapter]:
        """Get adapters dict for API access (backward compatibility)."""
        return {str(k.value): v for k, v in self._adapters.items()}

    def get_default_exchange(self) -> Optional[BaseAdapter]:
        """Get the default exchange adapter."""
        if "bybit" in self._adapters:
            return self._adapters["bybit"]
        if "okx" in self._adapters:
            return self._adapters["okx"]
        # Also check by Exchange enum value
        for exchange in Exchange:
            if exchange in self._adapters:
                return self._adapters[exchange]
        return None

    def get_exchange(self, name: str) -> Optional[BaseAdapter]:
        """Get exchange adapter by name."""
        name_lower = name.lower()
        # Check direct key match
        if name_lower in self._adapters:
            return self._adapters[name_lower]
        # Check by Exchange enum
        for exchange in Exchange:
            if exchange.value == name_lower and exchange in self._adapters:
                return self._adapters[exchange]
        return None

    def get_all_positions(self) -> List[Position]:
        """Get all positions from all exchanges via adapters."""
        positions = []
        for adapter in self._adapters.values():
            try:
                positions.extend(adapter.get_all_positions())
            except Exception:
                pass  # Skip adapters that fail
        return positions

    # ==================== Shutdown ====================

    def shutdown(self) -> None:
        """Shutdown the trading engine and disconnect adapters."""
        with self._lock:
            for exchange, adapter in self._adapters.items():
                try:
                    adapter.disconnect()
                except Exception as e:
                    print(f"Error disconnecting {exchange.value}: {e}")

            self._adapters.clear()