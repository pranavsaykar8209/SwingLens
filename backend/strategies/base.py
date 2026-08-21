from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import pandas as pd

from .models import SignalType, StrategySignal


class BaseStrategy(ABC):
    """
    Abstract Base Class for all SwingLens strategies.

    STRICT NO-LOOKAHEAD RULE:
    -------------------------
    Strategies MUST NOT look into future candles.
    When evaluating candle `i` in `generate_signals(df)` or during backtesting,
    the strategy must ONLY inspect historical data at or before index `i` (i.e. `df.iloc[:i+1]`).
    """

    name: str = "Base Strategy"
    version: str = "1.0.0"
    description: str = "Abstract base strategy interface"
    timeframe: str = "1d"
    required_indicators: List[str] = []
    default_parameters: Dict[str, Any] = {}

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        Initializes the strategy with user-defined parameter overrides merged on default_parameters.
        """
        self.parameters = {**self.default_parameters, **(parameters or {})}

    def get_metadata(self) -> Dict[str, Any]:
        """
        Returns structured metadata for registry discovery and UI inspection.
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "timeframe": self.timeframe,
            "required_indicators": self.required_indicators,
            "default_parameters": self.default_parameters,
            "parameters": self.parameters,
            "supported_signal_types": [s.value for s in SignalType],
        }

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> List[StrategySignal]:
        """
        Calculates signals for each historical candle in the provided DataFrame.

        Parameters:
        - df: pandas DataFrame containing OHLCV prices and required calculated indicators,
              sorted chronologically by `trade_date` ASC.

        Returns:
        - List of `StrategySignal` instances, one per evaluated candle.
        """
        pass

    def generate_latest_signal(self, df: pd.DataFrame) -> Optional[StrategySignal]:
        """
        Helper method returning the strategy signal for only the latest (most recent) candle.
        """
        signals = self.generate_signals(df)
        return signals[-1] if signals else None
