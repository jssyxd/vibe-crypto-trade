"""Strategy Generator using LLM to create trading strategies."""

import json
import os
import sys
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# Import backtest tool
import site
site_packages = site.getsitepackages()[0]
sys.path.insert(0, site_packages)

from src.tools.backtest_tool import run_backtest


@dataclass
class StrategySpec:
    """Strategy specification."""
    name: str
    description: str
    parameters: Dict[str, Any]
    code: str  # signal_engine.py code


class StrategyGenerator:
    """
    Generate trading strategies using natural language prompts.
    
    Uses template-based generation for reliability, with LLM for refinement.
    """

    # Strategy templates
    TEMPLATES = {
        "ma_crossover": {
            "description": "Moving Average Crossover Strategy",
            "parameters": {
                "fast_period": {"type": "int", "default": 20, "min": 5, "max": 50},
                "slow_period": {"type": "int", "default": 50, "min": 20, "max": 200},
            },
            "template": '''
import numpy as np
import pandas as pd
from typing import Dict

class SignalEngine:
    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        signals = {}
        for code, df in data_map.items():
            close = df['close']
            
            # Moving averages
            ma_fast = close.rolling(window={fast_period}).mean()
            ma_slow = close.rolling(window={slow_period}).mean()
            
            # Signal: 1 when fast crosses above slow
            signal = pd.Series(0.0, index=df.index)
            signal[ma_fast > ma_slow] = 1.0
            signal = signal.fillna(0)
            
            signals[code] = signal
        return signals
'''
        },
        "rsi_mean_reversion": {
            "description": "RSI Mean Reversion Strategy",
            "parameters": {
                "rsi_period": {"type": "int", "default": 14, "min": 5, "max": 30},
                "oversold": {"type": "int", "default": 30, "min": 20, "max": 40},
                "overbought": {"type": "int", "default": 70, "min": 60, "max": 80},
            },
            "template": '''
import numpy as np
import pandas as pd
from typing import Dict

class SignalEngine:
    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        signals = {}
        for code, df in data_map.items():
            close = df['close']
            
            # Calculate RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window={rsi_period}).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window={rsi_period}).mean()
            rs = gain / loss.replace(0, 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            # Signal: buy when oversold, sell when overbought
            signal = pd.Series(0.0, index=df.index)
            signal[rsi < {oversold}] = 1.0   # Buy
            signal[rsi > {overbought}] = 0.0  # Sell
            signal = signal.fillna(0)
            
            signals[code] = signal
        return signals
'''
        },
        "bollinger_bands": {
            "description": "Bollinger Bands Breakout Strategy",
            "parameters": {
                "period": {"type": "int", "default": 20, "min": 10, "max": 50},
                "std_dev": {"type": "float", "default": 2.0, "min": 1.5, "max": 3.0},
            },
            "template": '''
import numpy as np
import pandas as pd
from typing import Dict

class SignalEngine:
    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        signals = {}
        for code, df in data_map.items():
            close = df['close']
            
            # Bollinger Bands
            mid = close.rolling(window={period}).mean()
            std = close.rolling(window={period}).std()
            upper = mid + ({std_dev} * std)
            lower = mid - ({std_dev} * std)
            
            # Signal: buy when price touches lower band
            signal = pd.Series(0.0, index=df.index)
            signal[close < lower] = 1.0
            signal[close > mid] = 0.0  # Exit when back above mid
            signal = signal.fillna(0)
            
            signals[code] = signal
        return signals
'''
        },
        "momentum": {
            "description": "Momentum Strategy",
            "parameters": {
                "lookback": {"type": "int", "default": 20, "min": 5, "max": 60},
                "threshold": {"type": "float", "default": 0.02, "min": 0.01, "max": 0.10},
            },
            "template": '''
import numpy as np
import pandas as pd
from typing import Dict

class SignalEngine:
    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        signals = {}
        for code, df in data_map.items():
            close = df['close']
            
            # Momentum
            returns = close.pct_change({lookback})
            
            # Signal: buy when momentum is positive and strong
            signal = pd.Series(0.0, index=df.index)
            signal[returns > {threshold}] = 1.0
            signal[returns < 0] = 0.0
            signal = signal.fillna(0)
            
            signals[code] = signal
        return signals
'''
        },
    }

    def __init__(self):
        """Initialize Strategy Generator."""
        self.templates = self.TEMPLATES

    def list_templates(self) -> List[str]:
        """List available strategy templates."""
        return list(self.templates.keys())

    def get_template_info(self, template_name: str) -> Optional[Dict]:
        """Get template information."""
        if template_name not in self.templates:
            return None
        return {
            'name': template_name,
            'description': self.templates[template_name]['description'],
            'parameters': self.templates[template_name]['parameters'],
        }

    def generate(
        self,
        template_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> StrategySpec:
        """
        Generate strategy code from template.

        Args:
            template_name: Name of strategy template
            parameters: Strategy parameters

        Returns:
            StrategySpec with generated code
        """
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")

        template = self.templates[template_name]
        params = parameters or {}

        # Fill in default parameters
        full_params = {}
        for param_name, param_info in template['parameters'].items():
            if param_name in params:
                full_params[param_name] = params[param_name]
            else:
                full_params[param_name] = param_info['default']

        # Generate code from template using string replacement
        code = template['template']
        for param_name, value in full_params.items():
            code = code.replace(f'{{{param_name}}}', str(value))

        return StrategySpec(
            name=template_name,
            description=template['description'],
            parameters=full_params,
            code=code,
        )

    def save_strategy(
        self,
        spec: StrategySpec,
        run_dir: str,
        config_overrides: Optional[Dict] = None,
    ) -> str:
        """
        Save strategy to run directory.
        
        Args:
            spec: Strategy specification
            run_dir: Directory to save to
            config_overrides: Override config values
            
        Returns:
            Path to run directory
        """
        import os
        from pathlib import Path
        
        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        
        # Create code directory
        code_path = run_path / "code"
        code_path.mkdir(exist_ok=True)
        
        # Write signal_engine.py
        with open(code_path / "signal_engine.py", 'w') as f:
            f.write(spec.code)
        
        # Write or create config.json
        config_path = run_path / "config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {
                "source": "okx",
                "codes": ["BTC-USDT"],
                "start_date": "2024-01-01",
                "end_date": "2026-05-14",
                "interval": "1D",
                "initial_cash": 100000,
                "commission": 0.001,
                "extra_fields": None,
                "optimizer": None,
                "optimizer_params": {},
                "engine": "daily",
                "validation": None,
            }
        
        # Apply overrides
        if config_overrides:
            config.update(config_overrides)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Write strategy_info.json
        strategy_info = {
            'name': spec.name,
            'description': spec.description,
            'parameters': spec.parameters,
        }
        with open(run_path / "strategy_info.json", 'w') as f:
            json.dump(strategy_info, f, indent=2)
        
        return str(run_path)

    def run_backtest(self, run_dir: str) -> Dict[str, Any]:
        """
        Run backtest for strategy.
        
        Args:
            run_dir: Path to strategy directory
            
        Returns:
            Backtest result dict
        """
        result = run_backtest(run_dir)
        return json.loads(result)
