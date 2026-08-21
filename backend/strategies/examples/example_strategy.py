from typing import List
import pandas as pd

from ..base import BaseStrategy
from ..models import SignalType, StrategySignal
from ..registry import register_strategy


@register_strategy
class PassthroughHoldStrategy(BaseStrategy):
    """
    Architectural demonstrator strategy.
    Emits SignalType.HOLD for every historical candle to test framework compliance.
    Does NOT implement real trading logic.
    """

    name: str = "Passthrough Hold Strategy"
    version: str = "1.0.0"
    description: str = "Demonstrator strategy returning HOLD for all historical candles."
    timeframe: str = "1d"
    required_indicators: List[str] = []
    default_parameters: dict = {"holding_note": "Architectural test only"}

    def generate_signals(self, df: pd.DataFrame) -> List[StrategySignal]:
        signals: List[StrategySignal] = []
        if df.empty:
            return signals

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"

        for idx, row in df.iterrows():
            trade_date = str(row["trade_date"]) if "trade_date" in row else str(idx)
            close_price = float(row["close"]) if "close" in row else None

            signals.append(
                StrategySignal(
                    symbol=symbol,
                    strategy_name=self.name,
                    strategy_version=self.version,
                    signal=SignalType.HOLD,
                    signal_date=trade_date,
                    entry_price=close_price,
                    stop_loss=None,
                    target_price=None,
                    risk_reward=None,
                    score=0.0,
                    reason="Architectural passthrough hold signal",
                    metadata={"note": self.parameters.get("holding_note", "")},
                )
            )

        return signals
