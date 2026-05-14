"""Parameter Optimizer for adjusting strategy parameters based on results."""

import json
import random
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
from copy import deepcopy


@dataclass
class ParameterRange:
    """Parameter range specification."""
    name: str
    param_type: str  # "int", "float"
    current: float
    min_value: float
    max_value: float
    step: float = 1.0


class ParameterOptimizer:
    """
    Optimize strategy parameters using grid search and random search.
    
    Strategies:
    - Grid search: systematically explore parameter space
    - Random search: randomly sample parameter combinations
    - Bayesian-inspired: adjust towards better-performing regions
    """

    def __init__(
        self,
        search_strategy: str = "random",  # "grid", "random", "bayesian"
        max_iterations: int = 10,
    ):
        self.search_strategy = search_strategy
        self.max_iterations = max_iterations
        self.history: List[Dict] = []

    def suggest_parameters(
        self,
        current_params: Dict[str, Any],
        param_ranges: Dict[str, ParameterRange],
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Suggest new parameters based on search strategy.
        
        Args:
            current_params: Current parameter values
            param_ranges: Parameter range specifications
            iteration: Current iteration number
            
        Returns:
            New parameter values to try
        """
        if self.search_strategy == "grid":
            return self._grid_search(current_params, param_ranges, iteration)
        elif self.search_strategy == "random":
            return self._random_search(current_params, param_ranges)
        elif self.search_strategy == "bayesian":
            return self._bayesian_search(current_params, param_ranges, iteration)
        else:
            return self._random_search(current_params, param_ranges)

    def _grid_search(
        self,
        current_params: Dict[str, Any],
        param_ranges: Dict[str, ParameterRange],
        iteration: int,
    ) -> Dict[str, Any]:
        """Grid search: step through parameter space systematically."""
        new_params = {}
        n_params = len(param_ranges)
        
        # Simple grid: vary one parameter at a time
        param_names = list(param_ranges.keys())
        param_idx = iteration % n_params
        param_name = param_names[param_idx]
        param_range = param_ranges[param_name]
        
        for name, value in current_params.items():
            if name == param_name:
                # Step this parameter
                current_idx = int((value - param_range.min_value) / param_range.step)
                next_idx = (current_idx + 1) % int((param_range.max_value - param_range.min_value) / param_range.step)
                new_value = param_range.min_value + next_idx * param_range.step
                
                if param_range.param_type == "int":
                    new_params[name] = int(new_value)
                else:
                    new_params[name] = round(new_value, 2)
            else:
                new_params[name] = value
        
        return new_params

    def _random_search(
        self,
        current_params: Dict[str, Any],
        param_ranges: Dict[str, ParameterRange],
    ) -> Dict[str, Any]:
        """Random search: randomly sample parameter combinations."""
        new_params = {}
        
        for name, param_range in param_ranges.items():
            if param_range.param_type == "int":
                # Random integer
                n_steps = int((param_range.max_value - param_range.min_value) / param_range.step)
                if n_steps > 0:
                    step_idx = random.randint(0, n_steps)
                    new_value = int(param_range.min_value + step_idx * param_range.step)
                else:
                    new_value = int(param_range.current)
            else:
                # Random float
                new_value = random.uniform(param_range.min_value, param_range.max_value)
                new_value = round(new_value, 2)
            
            new_params[name] = new_value
        
        return new_params

    def _bayesian_search(
        self,
        current_params: Dict[str, Any],
        param_ranges: Dict[str, ParameterRange],
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Bayesian-inspired search: adjust towards better regions.
        
        Uses simple heuristic: if score improved, continue in that direction.
        """
        if len(self.history) < 2:
            return self._random_search(current_params, param_ranges)
        
        # Check if last iteration improved
        last_score = self.history[-1].get('score', 0)
        prev_score = self.history[-2].get('score', 0)
        
        new_params = {}
        for name, param_range in param_ranges.items():
            last_value = self.history[-1]['params'].get(name, param_range.current)
            prev_value = self.history[-2]['params'].get(name, param_range.current)
            
            if last_score > prev_score:
                # Improvement: continue in same direction
                delta = last_value - prev_value
                new_value = last_value + delta * 0.5
            else:
                # No improvement: reverse direction or random
                delta = last_value - prev_value
                new_value = last_value - delta * 0.3 + random.uniform(-param_range.step, param_range.step)
            
            # Clamp to range
            new_value = max(param_range.min_value, min(param_range.max_value, new_value))
            
            if param_range.param_type == "int":
                new_value = int(round(new_value / param_range.step)) * int(param_range.step)
            
            new_params[name] = new_value
        
        return new_params

    def record_result(
        self,
        params: Dict[str, Any],
        score: float,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        """Record parameter search result."""
        self.history.append({
            'params': params,
            'score': score,
            'metrics': metrics or {},
        })

    def get_best_parameters(self) -> Optional[Dict[str, Any]]:
        """Get best parameters from history."""
        if not self.history:
            return None
        
        best = max(self.history, key=lambda x: x['score'])
        return best['params']

    def get_best_score(self) -> float:
        """Get best score from history."""
        if not self.history:
            return 0.0
        return max(h['score'] for h in self.history)

    def should_continue(self, iteration: int, improvement_threshold: float = 0.01) -> bool:
        """
        Determine if optimization should continue.
        
        Args:
            iteration: Current iteration
            improvement_threshold: Minimum improvement to continue
            
        Returns:
            True if should continue, False if should stop
        """
        if iteration >= self.max_iterations:
            return False
        
        if len(self.history) < 2:
            return True
        
        # Check if recent improvement is significant
        recent_scores = [h['score'] for h in self.history[-3:]]
        if len(recent_scores) >= 2:
            improvement = recent_scores[-1] - recent_scores[0]
            if improvement < improvement_threshold:
                return False
        
        return True

    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization process."""
        if not self.history:
            return {'iterations': 0, 'best_score': 0, 'best_params': None}
        
        best = max(self.history, key=lambda x: x['score'])
        
        return {
            'iterations': len(self.history),
            'best_score': best['score'],
            'best_params': best['params'],
            'all_scores': [h['score'] for h in self.history],
        }
