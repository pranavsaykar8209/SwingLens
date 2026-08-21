from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from .base import BaseStrategy
from .models import SignalType, StrategySignal
from .registry import register_strategy


@register_strategy
class EMAPullbackStrategy(BaseStrategy):
    """
    EMA Pullback Strategy v1.0

    Enters long swing positions when price in a strong uptrend (EMA20 > EMA50 > EMA200)
    pulls back near the EMA20 and confirms momentum (RSI 50-65), bullish breakout over
    previous candle's high, and strong volume.
    """

    name: str = "EMA Pullback"
    version: str = "1.0"
    description: str = (
        "Swing trading strategy entering bullish pullbacks near EMA20 in an "
        "established trend with RSI and volume confirmation."
    )
    timeframe: str = "1d"
    required_indicators: List[str] = [
        "ema_20",
        "ema_50",
        "ema_200",
        "rsi_14",
        "atr_14",
        "volume_sma_20",
    ]
    default_parameters: Dict[str, Any] = {
        "ema_fast": 20,
        "ema_trend": 50,
        "ema_long": 200,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 65.0,
        "atr_period": 14,
        "atr_stop_multiplier": 1.5,
        "reward_risk_ratio": 2.0,
        "pullback_distance_percent": 2.0,
        "volume_period": 20,
        "volume_multiplier": 1.0,
    }

    def generate_signals(self, df: pd.DataFrame) -> List[StrategySignal]:
        signals: List[StrategySignal] = []
        if df.empty:
            return signals

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"

        ema_fast_col = f"ema_{self.parameters['ema_fast']}"
        ema_trend_col = f"ema_{self.parameters['ema_trend']}"
        ema_long_col = f"ema_{self.parameters['ema_long']}"
        rsi_col = f"rsi_{self.parameters['rsi_period']}"
        atr_col = f"atr_{self.parameters['atr_period']}"
        vol_sma_col = f"volume_sma_{self.parameters['volume_period']}"

        # Fast direct iteration over pre-computed indicator columns
        for idx in range(len(df)):
            curr_row = df.iloc[idx]
            trade_date = str(curr_row["trade_date"]) if "trade_date" in curr_row else str(idx)

            # Check indicator column presence
            req_cols = [ema_fast_col, ema_trend_col, ema_long_col, rsi_col, atr_col, vol_sma_col]
            missing_cols = [c for c in req_cols if c not in curr_row]

            if missing_cols:
                signals.append(self._create_hold_signal(symbol, trade_date, "Missing indicator columns"))
                continue

            # Extract indicator values for current candle
            ema20 = curr_row[ema_fast_col]
            ema50 = curr_row[ema_trend_col]
            ema200 = curr_row[ema_long_col]
            rsi14 = curr_row[rsi_col]
            atr14 = curr_row[atr_col]
            vol_sma = curr_row[vol_sma_col]

            close_p = float(curr_row["close"]) if "close" in curr_row else None
            vol = float(curr_row["volume"]) if "volume" in curr_row else None

            # Warm-up check: return HOLD if any required indicator is NaN/None
            if (
                close_p is None
                or vol is None
                or pd.isna(ema20)
                or pd.isna(ema50)
                or pd.isna(ema200)
                or pd.isna(rsi14)
                or pd.isna(atr14)
                or pd.isna(vol_sma)
                or atr14 <= 0
                or vol_sma <= 0
            ):
                signals.append(self._create_hold_signal(symbol, trade_date, "Indicator warm-up period incomplete"))
                continue

            # Need at least 2 candles to check bullish confirmation (Close_N > High_{N-1})
            if idx < 1:
                signals.append(self._create_hold_signal(symbol, trade_date, "Insufficient history for confirmation"))
                continue

            prev_row = df.iloc[idx - 1]
            prev_high = float(prev_row["high"])

            # ----------------------------------------------------
            # Evaluate all 8 Long Entry Setup Conditions
            # ----------------------------------------------------

            # 1. Fast trend: EMA20 > EMA50
            cond1_trend_fast = ema20 > ema50

            # 2. Long trend: EMA50 > EMA200
            cond2_trend_long = ema50 > ema200

            # 3. Price above EMA200: Close > EMA200
            cond3_above_ema200 = close_p > ema200

            # 4. Pullback distance: abs(close - EMA20) / EMA20 <= threshold
            dist_pct = abs(close_p - ema20) / ema20 * 100.0
            cond4_pullback = dist_pct <= float(self.parameters["pullback_distance_percent"])

            # 5. RSI range: rsi_min <= RSI <= rsi_max
            cond5_rsi = float(self.parameters["rsi_min"]) <= rsi14 <= float(self.parameters["rsi_max"])

            # 6. Bullish confirmation: Close > prev_high
            cond6_bullish_confirm = close_p > prev_high

            # 7. Volume confirmation: Volume >= Volume_SMA20 * volume_multiplier
            vol_ratio = vol / vol_sma if vol_sma > 0 else 0.0
            cond7_volume = vol >= (vol_sma * float(self.parameters["volume_multiplier"]))

            # 8. ATR availability checked during warm-up (atr14 > 0)

            all_conditions_pass = (
                cond1_trend_fast
                and cond2_trend_long
                and cond3_above_ema200
                and cond4_pullback
                and cond5_rsi
                and cond6_bullish_confirm
                and cond7_volume
            )

            if all_conditions_pass:
                # Calculate Stop Loss and Target Price
                atr_multiplier = float(self.parameters["atr_stop_multiplier"])
                rr_ratio = float(self.parameters["reward_risk_ratio"])

                stop_loss = close_p - (atr14 * atr_multiplier)
                risk = close_p - stop_loss
                target_price = close_p + (risk * rr_ratio)

                reason_str = (
                    f"EMA20 ({ema20:.2f}) > EMA50 ({ema50:.2f}) > EMA200 ({ema200:.2f}), "
                    f"pullback {dist_pct:.1f}% from EMA20, RSI14={rsi14:.1f}, "
                    f"bullish confirmation (Close {close_p:.2f} > PrevHigh {prev_high:.2f}), "
                    f"volume {vol_ratio:.1f}x avg."
                )

                metadata_dict = {
                    "ema20": round(float(ema20), 2),
                    "ema50": round(float(ema50), 2),
                    "ema200": round(float(ema200), 2),
                    "rsi14": round(float(rsi14), 2),
                    "atr14": round(float(atr14), 2),
                    "volume": float(vol),
                    "volume_sma20": round(float(vol_sma), 2),
                    "volume_ratio": round(float(vol_ratio), 2),
                    "pullback_distance_pct": round(float(dist_pct), 2),
                }

                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        strategy_name=self.name,
                        strategy_version=self.version,
                        signal=SignalType.BUY,
                        signal_date=trade_date,
                        entry_price=round(close_p, 2),
                        stop_loss=round(stop_loss, 2),
                        target_price=round(target_price, 2),
                        score=0.85,
                        reason=reason_str,
                        metadata=metadata_dict,
                    )
                )
            else:
                signals.append(self.create_hold_reason_signal(symbol, trade_date, close_p))

        return signals

    def _create_hold_signal(self, symbol: str, trade_date: str, reason: str) -> StrategySignal:
        return StrategySignal(
            symbol=symbol,
            strategy_name=self.name,
            strategy_version=self.version,
            signal=SignalType.HOLD,
            signal_date=trade_date,
            reason=reason,
        )

    def create_hold_reason_signal(self, symbol: str, trade_date: str, close_price: float) -> StrategySignal:
        return StrategySignal(
            symbol=symbol,
            strategy_name=self.name,
            strategy_version=self.version,
            signal=SignalType.HOLD,
            signal_date=trade_date,
            entry_price=round(close_price, 2),
            reason="Setup conditions not satisfied",
        )
