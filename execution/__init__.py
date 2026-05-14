"""
Vibe-Crypto-Trading Execution Layer

Modules:
- adapters: Exchange adapters (Bybit, OKX)
- risk: Risk controller (position, leverage, drawdown)
- signals: Signal queue for order processing
- core: Core execution engine
"""

from .core.execution_engine import ExecutionEngine
from .risk.risk_controller import RiskController
from .signals.signal_queue import SignalQueue

__all__ = ["ExecutionEngine", "RiskController", "SignalQueue"]
