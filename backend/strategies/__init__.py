# SwingLens Strategy Engine Framework
from .models import SignalType, StrategySignal
from .base import BaseStrategy
from .registry import (
    StrategyRegistry,
    register_strategy,
    get_strategy,
    list_strategies,
)
from .examples.example_strategy import PassthroughHoldStrategy
from .ema_pullback import EMAPullbackStrategy

__all__ = [
    "SignalType",
    "StrategySignal",
    "BaseStrategy",
    "StrategyRegistry",
    "register_strategy",
    "get_strategy",
    "list_strategies",
    "PassthroughHoldStrategy",
    "EMAPullbackStrategy",
]
