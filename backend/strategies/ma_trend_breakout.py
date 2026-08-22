from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from .base import BaseStrategy
from .models import SignalType, StrategySignal
from .registry import register_strategy


@register_strategy
class MATrendBreakoutStrategy(BaseStrategy):
    """
    MA Trend Breakout Strategy v1.0

    A swing-trading trend-following strategy that enters long positions when:
    1. Stock is in a bullish long-term trend (EMA50 > EMA200 and Close > EMA200).
    2. Today's close breaks above the highest high of the previous 20 trading sessions
       (excluding today's candle).
    3. Meaningful volume confirmation (Volume >= 1.5x 20-day Volume SMA).
    4. RSI14 between 50 and 70.
    """

    name: str = "MA Trend Breakout"
    version: str = "1.0"
    description: str = (
        "Swing trading trend-following breakout strategy entering when price breaks "
        "20-day high with bullish EMA alignment, volume, and RSI confirmation."
    )
    timeframe: str = "1d"
    required_indicators: List[str] = [
        "ema_50",
        "ema_200",
        "rsi_14",
        "atr_14",
        "highest_high_20",
        "volume_sma_20",
    ]
    default_parameters: Dict[str, Any] = {
        "ema_fast": 50,
        "ema_slow": 200,
        "breakout_period": 20,
        "volume_period": 20,
        "volume_multiplier": 1.5,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 70.0,
        "atr_period": 14,
        "atr_stop_multiplier": 1.5,
        "reward_risk_ratio": 2.0,
    }

    def generate_signals(self, df: pd.DataFrame) -> List[StrategySignal]:
        signals: List[StrategySignal] = []
        if df.empty:
            return signals

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"

        ema_fast_col = f"ema_{self.parameters['ema_fast']}"
        ema_slow_col = f"ema_{self.parameters['ema_slow']}"
        rsi_col = f"rsi_{self.parameters['rsi_period']}"
        atr_col = f"atr_{self.parameters['atr_period']}"
        vol_sma_col = f"volume_sma_{self.parameters['volume_period']}"
        breakout_period = int(self.parameters["breakout_period"])
        hh_col = f"highest_high_{breakout_period}"

        for idx in range(len(df)):
            curr_row = df.iloc[idx]
            trade_date = str(curr_row["trade_date"]) if "trade_date" in curr_row else str(idx)

            # Check indicator column presence
            req_cols = [ema_fast_col, ema_slow_col, rsi_col, atr_col, vol_sma_col]
            missing_cols = [c for c in req_cols if c not in curr_row]

            if missing_cols:
                signals.append(self._create_hold_signal(symbol, trade_date, "Missing indicator columns"))
                continue

            # Extract indicator values for current candle
            ema50 = curr_row[ema_fast_col]
            ema200 = curr_row[ema_slow_col]
            rsi14 = curr_row[rsi_col]
            atr14 = curr_row[atr_col]
            vol_sma = curr_row[vol_sma_col]

            close_p = float(curr_row["close"]) if "close" in curr_row else None
            vol = float(curr_row["volume"]) if "volume" in curr_row else None

            # Warm-up check: return HOLD if any required indicator is NaN/None
            if (
                close_p is None
                or vol is None
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

            # Need at least `breakout_period` previous candles to calculate previous N-day high (excluding today)
            if idx < breakout_period:
                signals.append(
                    self._create_hold_signal(
                        symbol, trade_date, f"Insufficient history for previous {breakout_period}-day high calculation"
                    )
                )
                continue

            # Calculate previous 20-day high (candles t-20 through t-1, excluding today's candle t)
            if hh_col in df.columns and not pd.isna(df.iloc[idx - 1][hh_col]):
                previous_20_high = float(df.iloc[idx - 1][hh_col])
            else:
                previous_20_high = float(df["high"].iloc[idx - breakout_period : idx].max())

            if pd.isna(previous_20_high):
                signals.append(
                    self._create_hold_signal(
                        symbol, trade_date, f"Insufficient history for previous {breakout_period}-day high calculation"
                    )
                )
                continue

            # ----------------------------------------------------
            # Evaluate Strategy Conditions
            # ----------------------------------------------------

            # 1. Bullish trend: EMA50 > EMA200
            cond1_trend_ema = ema50 > ema200

            # 2. Price above EMA200: Close > EMA200
            cond2_price_above_ema200 = close_p > ema200

            # 3. 20-day Breakout: Today's Close > Previous 20-day High
            cond3_breakout = close_p > previous_20_high

            # 4. Volume confirmation: Today's Volume >= 1.5 * Volume SMA20
            vol_multiplier = float(self.parameters["volume_multiplier"])
            vol_ratio = vol / vol_sma if vol_sma > 0 else 0.0
            cond4_volume = vol >= (vol_sma * vol_multiplier)

            # 5. RSI confirmation: 50 <= RSI14 <= 70
            rsi_min = float(self.parameters["rsi_min"])
            rsi_max = float(self.parameters["rsi_max"])
            cond5_rsi = rsi_min <= rsi14 <= rsi_max

            all_conditions_pass = (
                cond1_trend_ema
                and cond2_price_above_ema200
                and cond3_breakout
                and cond4_volume
                and cond5_rsi
            )

            if all_conditions_pass:
                atr_multiplier = float(self.parameters["atr_stop_multiplier"])
                rr_ratio = float(self.parameters["reward_risk_ratio"])

                stop_loss = close_p - (atr14 * atr_multiplier)
                if stop_loss >= close_p:
                    signals.append(self.create_hold_reason_signal(symbol, trade_date, close_p))
                    continue

                risk = close_p - stop_loss
                target_price = close_p + (risk * rr_ratio)

                # Deterministic signal score (0.0 to 1.0)
                vol_comp = min(0.20, max(0.0, (vol_ratio - vol_multiplier) * 0.20))
                breakout_pct = (close_p - previous_20_high) / previous_20_high * 100.0
                breakout_comp = min(0.15, max(0.0, breakout_pct * 0.05))
                trend_dist_pct = (close_p - ema200) / ema200 * 100.0
                trend_comp = min(0.10, max(0.0, trend_dist_pct * 0.02))
                rsi_comp = min(0.05, max(0.0, 0.05 - abs(rsi14 - 60.0) * 0.005))
                score_val = round(min(0.99, max(0.50, 0.50 + vol_comp + breakout_comp + trend_comp + rsi_comp)), 2)

                reason_str = (
                    f"EMA50 (₹{ema50:.2f}) > EMA200 (₹{ema200:.2f}), "
                    f"close (₹{close_p:.2f}) broke previous 20-day high (₹{previous_20_high:.2f}), "
                    f"volume {vol_ratio:.1f}x average, "
                    f"RSI14={rsi14:.1f}."
                )

                metadata_dict = {
                    "ema50": round(float(ema50), 2),
                    "ema200": round(float(ema200), 2),
                    "rsi14": round(float(rsi14), 2),
                    "atr14": round(float(atr14), 2),
                    "previous_20_high": round(float(previous_20_high), 2),
                    "volume_sma20": round(float(vol_sma), 2),
                    "volume_ratio": round(float(vol_ratio), 2),
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
                        score=score_val,
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
