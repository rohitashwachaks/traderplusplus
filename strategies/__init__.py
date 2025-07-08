
import pkgutil
import importlib
import inspect
from .base import StrategyFactory, StrategyBase

for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{module_name}")
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, StrategyBase) and obj is not StrategyBase:
            StrategyFactory.register_strategy(name, obj)
