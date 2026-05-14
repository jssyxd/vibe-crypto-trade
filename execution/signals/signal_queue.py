"""Signal Queue for order processing."""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path


class SignalPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2


@dataclass
class TradingSignal:
    """Trading signal from strategy."""
    signal_id: str
    timestamp: datetime
    symbol: str
    side: str  # "buy" or "sell"
    strategy_name: str
    quantity: float
    price: Optional[float] = None
    priority: SignalPriority = SignalPriority.NORMAL
    metadata: Dict[str, Any] = None
    status: str = "pending"  # pending, processed, rejected, filled
    order_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        d['priority'] = self.priority.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'TradingSignal':
        d['timestamp'] = datetime.fromisoformat(d['timestamp'])
        d['priority'] = SignalPriority(d['priority'])
        return cls(**d)


class SignalQueue:
    """
    Signal Queue for managing trading signals.

    Features:
    - Priority-based ordering
    - Persistent storage
    - Status tracking
    """

    def __init__(self, storage_path: str = "execution/signals/queue.json"):
        """
        Initialize Signal Queue.

        Args:
            storage_path: Path to JSON file for persistence
        """
        self.storage_path = storage_path
        self._signals: List[TradingSignal] = []
        self._load()

    def _load(self):
        """Load signals from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self._signals = [TradingSignal.from_dict(d) for d in data]
            except Exception as e:
                print(f"Error loading signals: {e}")
                self._signals = []

    def _save(self):
        """Save signals to storage."""
        try:
            Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump([s.to_dict() for s in self._signals], f, indent=2)
        except Exception as e:
            print(f"Error saving signals: {e}")

    def add(self, signal: TradingSignal) -> str:
        """
        Add signal to queue.

        Args:
            signal: Trading signal to add

        Returns:
            Signal ID
        """
        self._signals.append(signal)
        self._sort()
        self._save()
        return signal.signal_id

    def _sort(self):
        """Sort signals by priority (high first) then timestamp."""
        self._signals.sort(
            key=lambda s: (-s.priority.value, s.timestamp)
        )

    def get_pending(self) -> List[TradingSignal]:
        """Get all pending signals."""
        return [s for s in self._signals if s.status == "pending"]

    def get_next(self) -> Optional[TradingSignal]:
        """Get next pending signal (highest priority)."""
        pending = self.get_pending()
        return pending[0] if pending else None

    def mark_processed(self, signal_id: str, order_id: str = None,
                       status: str = "processed", error: str = None):
        """Mark signal as processed."""
        for signal in self._signals:
            if signal.signal_id == signal_id:
                signal.status = status
                signal.order_id = order_id
                signal.error = error
                break
        self._save()

    def get_by_status(self, status: str) -> List[TradingSignal]:
        """Get signals by status."""
        return [s for s in self._signals if s.status == status]

    def clear_processed(self, before_hours: int = 24):
        """Clear processed signals older than specified hours."""
        cutoff = datetime.now() - timedelta(hours=before_hours)
        self._signals = [
            s for s in self._signals
            if s.status == "pending" or s.timestamp > cutoff
        ]
        self._save()

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        return {
            'total': len(self._signals),
            'pending': len(self.get_pending()),
            'processed': len(self.get_by_status('processed')),
            'rejected': len(self.get_by_status('rejected')),
            'filled': len(self.get_by_status('filled')),
        }
