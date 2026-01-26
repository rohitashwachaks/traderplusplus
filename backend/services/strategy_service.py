from typing import List, Optional
import importlib
import inspect
import pkgutil

from backend.api.models import StrategyInfo
from strategies.base import StrategyBase


class StrategyService:
    def __init__(self):
        self._strategies_cache = None
    
    def _discover_strategies(self) -> List[StrategyInfo]:
        strategies = []
        
        strategy_modules = [
            ("strategies.single_asset", "Single Asset"),
            ("strategies.multi_asset", "Multi Asset"),
            ("strategies.derivatives", "Derivatives")
        ]
        
        for module_path, category in strategy_modules:
            try:
                module = importlib.import_module(module_path)
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, StrategyBase) and obj != StrategyBase:
                        strategy_name = name.replace("Strategy", "").lower()
                        if strategy_name.endswith("_"):
                            strategy_name = strategy_name[:-1]
                        
                        strategies.append(StrategyInfo(
                            name=strategy_name,
                            description=obj.__doc__ or f"{name} strategy",
                            category=category,
                            parameters=self._extract_parameters(obj)
                        ))
            except (ImportError, AttributeError) as e:
                print(f"Could not load strategies from {module_path}: {e}")
        
        return strategies
    
    def _extract_parameters(self, strategy_class) -> dict:
        try:
            init_signature = inspect.signature(strategy_class.__init__)
            params = {}
            
            for param_name, param in init_signature.parameters.items():
                if param_name in ['self', 'tickers']:
                    continue
                
                params[param_name] = {
                    "default": param.default if param.default != inspect.Parameter.empty else None,
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                }
            
            return params
        except Exception:
            return {}
    
    def list_strategies(self) -> List[StrategyInfo]:
        if self._strategies_cache is None:
            self._strategies_cache = self._discover_strategies()
        
        return self._strategies_cache
    
    def get_strategy(self, strategy_name: str) -> Optional[StrategyInfo]:
        strategies = self.list_strategies()
        
        for strategy in strategies:
            if strategy.name == strategy_name:
                return strategy
        
        return None
