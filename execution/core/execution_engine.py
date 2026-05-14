"""Execution Engine - orchestrates strategy signals to exchange execution."""

import os
from datetime import datetime
from typing import Dict, Optional, Any

from execution.adapters import BybitAdapter, OKXAdapter, BaseAdapter
from execution.risk.risk_controller import RiskController, RiskLimits
from execution.signals.signal_queue import SignalQueue, TradingSignal, SignalPriority


class ExecutionEngine:
    """
    Execution Engine that coordinates:
    - Exchange adapters (Bybit, OKX)
    - Risk controller
    - Signal queue
    """

    def __init__(
        self,
        exchange: str = "bybit",
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
        risk_limits: Optional[RiskLimits] = None,
    ):
        """
        Initialize Execution Engine.

        Args:
            exchange: Exchange to use ("bybit" or "okx")
            api_key: Exchange API key
            api_secret: Exchange API secret
            testnet: Use testnet/simulation
            risk_limits: Risk limit configuration
        """
        self.exchange_name = exchange

        # Initialize exchange adapter
        if exchange.lower() == "bybit":
            self.exchange = BybitAdapter(api_key, api_secret, testnet)
        elif exchange.lower() == "okx":
            self.exchange = OKXAdapter(api_key, api_secret, testnet)
        else:
            raise ValueError(f"Unknown exchange: {exchange}")

        # Initialize risk controller
        self.risk = RiskController(risk_limits or RiskLimits())

        # Initialize signal queue
        self.queue = SignalQueue()

        # Track last signal per symbol to avoid duplicates
        self._last_signals: Dict[str, datetime] = {}

    def connect(self) -> bool:
        """Connect to exchange."""
        return self.exchange.connect()

    def disconnect(self) -> bool:
        """Disconnect from exchange."""
        return self.exchange.disconnect()

    def process_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """
        Process a trading signal through risk checks and execution.

        Args:
            signal: Trading signal to process

        Returns:
            Result dict with status, order_id, etc.
        """
        result = {
            'signal_id': signal.signal_id,
            'symbol': signal.symbol,
            'status': 'rejected',
            'message': '',
            'order_id': None,
        }

        # Get current balance and ticker
        balance = self.exchange.get_balance()
        ticker = self.exchange.get_ticker(signal.symbol)

        current_price = ticker.get('last', 0)
        portfolio_value = balance.total_equity

        # Check risk controls
        risk_check = self.risk.check_order(
            symbol=signal.symbol,
            side=signal.side,
            quantity=signal.quantity,
            price=current_price,
            portfolio_value=portfolio_value,
        )

        if not risk_check.approved:
            result['status'] = 'rejected'
            result['message'] = risk_check.message
            self.queue.mark_processed(signal.signal_id, status='rejected', error=risk_check.message)
            return result

        # Apply risk adjustments if any
        quantity = signal.quantity
        if 'quantity' in risk_check.adjustments:
            quantity = risk_check.adjustments['quantity']
            result['message'] = risk_check.message

        # Place order
        from execution.adapters.base_adapter import OrderSide, OrderType

        side = OrderSide.BUY if signal.side.lower() == 'buy' else OrderSide.SELL
        order_type = OrderType.MARKET if not signal.price else OrderType.LIMIT

        try:
            order = self.exchange.place_order(
                symbol=signal.symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=signal.price,
            )

            result['status'] = 'filled' if order.status.value == 'filled' else 'pending'
            result['order_id'] = order.order_id
            result['message'] = f"Order {result['status']}: {order.order_id}"
            result['filled_qty'] = order.filled_qty
            result['avg_price'] = order.avg_fill_price

            self.queue.mark_processed(
                signal.signal_id,
                order_id=order.order_id,
                status='filled' if order.status.value == 'filled' else 'processed',
            )

        except Exception as e:
            result['status'] = 'error'
            result['message'] = str(e)
            self.queue.mark_processed(signal.signal_id, status='rejected', error=str(e))

        return result

    def process_pending_signals(self) -> Dict[str, Any]:
        """Process all pending signals in queue."""
        results = []
        processed = 0

        while True:
            signal = self.queue.get_next()
            if not signal:
                break

            result = self.process_signal(signal)
            results.append(result)
            processed += 1

            # Limit processing per call
            if processed >= 10:
                break

        return {
            'processed': processed,
            'results': results,
            'queue_stats': self.queue.get_stats(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get execution engine status."""
        balance = self.exchange.get_balance()
        risk_status = self.risk.get_status()
        queue_stats = self.queue.get_stats()

        return {
            'exchange': self.exchange_name,
            'connected': self.exchange.connected,
            'balance': {
                'total': balance.total_equity,
                'available': balance.available_balance,
                'locked': balance.locked_balance,
            },
            'risk': risk_status,
            'queue': queue_stats,
        }
