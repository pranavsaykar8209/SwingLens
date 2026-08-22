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
from .ma_trend_breakout import MATrendBreakoutStrategy
from .rsi_mean_reversion import RSIMeanReversionStrategy
from .macd_momentum import MACDMomentumStrategy

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
    "MATrendBreakoutStrategy",
    "RSIMeanReversionStrategy",
    "MACDMomentumStrategy",
]



