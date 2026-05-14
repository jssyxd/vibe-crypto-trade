"""
Bybit Live Data Adapter using CCXT and WebSocket.
Provides real-time market data and order book access.
"""

import ccxt
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import threading
import queue

class BybitLiveAdapter:
    """
    Bybit live data adapter for real-time trading.
    """

    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.exchange = ccxt.bybit({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'testnet': testnet,
            },
        })
        self._running = False
        self._price_callbacks: List[Callable[[str, float], None]] = []
        self._orderbook_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self._thread: Optional[threading.Thread] = None
        self._queue: queue.Queue = queue.Queue()
        self._use_simulation = False

    def connect(self) -> bool:
        """Connect to Bybit."""
        try:
            # Test connection
            self.exchange.fetch_ticker('BTC/USDT')
            self._running = True
            return True
        except Exception as e:
            print(f"Bybit connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from Bybit."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def on_price_update(self, callback: Callable[[str, float], None]):
        """Register callback for price updates."""
        self._price_callbacks.append(callback)

    def on_orderbook_update(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Register callback for order book updates."""
        self._orderbook_callbacks.append(callback)

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        try:
            ticker = self.exchange.fetch_ticker(symbol.replace('-', '/'))
            return ticker.get('last')
        except Exception as e:
            print(f"Error fetching price: {e}")
            return None

    def get_order_book(self, symbol: str, limit: int = 20) -> Optional[Dict[str, Any]]:
        """Get order book for symbol."""
        try:
            ob = self.exchange.fetch_order_book(symbol.replace('-', '/'), limit)
            return {
                'bids': ob.get('bids', []),
                'asks': ob.get('asks', []),
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"Error fetching order book: {e}")
            return None

    def get_recent_trades(self, symbol: str, limit: int = 50) -> list:
        """Get recent trades for symbol."""
        try:
            trades = self.exchange.fetch_trades(symbol.replace('-', '/'), limit=limit)
            return [
                {
                    'id': t.get('id'),
                    'price': t.get('price'),
                    'amount': t.get('amount'),
                    'side': t.get('side'),
                    'timestamp': t.get('timestamp'),
                }
                for t in trades
            ]
        except Exception as e:
            print(f"Error fetching trades: {e}")
            return []

    def get_funding_rate(self, symbol: str = "BTC/USDT") -> Optional[float]:
        """Get current funding rate for perpetual."""
        try:
            market = self.exchange.market(symbol)
            if 'fundingRate' in market:
                return market['fundingRate']
            return None
        except Exception:
            return None

    def get_kline(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> list:
        """Get kline/candlestick data."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol.replace('-', '/'), timeframe, limit=limit)
            return [
                {
                    'timestamp': k[0],
                    'open': k[1],
                    'high': k[2],
                    'low': k[3],
                    'close': k[4],
                    'volume': k[5],
                }
                for k in ohlcv
            ]
        except Exception as e:
            print(f"Error fetching klines: {e}")
            return []

    def get_24h_stats(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get 24h trading statistics."""
        try:
            ticker = self.exchange.fetch_ticker(symbol.replace('-', '/'))
            return {
                'symbol': symbol,
                'last': ticker.get('last'),
                'high': ticker.get('high'),
                'low': ticker.get('low'),
                'volume': ticker.get('baseVolume'),
                'quote_volume': ticker.get('quoteVolume'),
                'change': ticker.get('change'),
                'change_percent': ticker.get('percentage'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"Error fetching 24h stats: {e}")
            return None