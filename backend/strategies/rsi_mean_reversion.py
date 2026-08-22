from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from .base import BaseStrategy
from .models import SignalType, StrategySignal
from .registry import register_strategy


@register_strategy
class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean-Reversion Strategy v1.0

    A swing-trading strategy that enters long positions when:
    1. Stock is in a bullish long-term trend (Close > EMA200 and EMA50 > EMA200).
    2. Stock recently became oversold (Previous RSI14 < 40) and today's RSI is recovering (Today's RSI14 > Previous RSI14).
    3. Price is pulling back toward EMA20 (Close within 3% of EMA20).
    4. Bullish confirmation candle (Close > Open and Close > Previous Day's High).
    5. Volume confirmation (Volume >= 1.0x 20-day Volume SMA).
    """

    name: str = "RSI Mean-Reversion"
    version: str = "1.0"
    description: str = (
        "Swing trading mean-reversion strategy entering when RSI recovers from oversold "
        "territory near EMA20 in an established bullish trend with price and volume confirmation."
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
        "rsi_oversold_max": 40.0,
        "distance_from_ema20_percent": 3.0,
        "volume_period": 20,
        "volume_multiplier": 1.0,
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
        ema_trend_col = f"ema_{self.parameters['ema_trend']}"
        ema_long_col = f"ema_{self.parameters['ema_long']}"
        rsi_col = f"rsi_{self.parameters['rsi_period']}"
        atr_col = f"atr_{self.parameters['atr_period']}"
        vol_sma_col = f"volume_sma_{self.parameters['volume_period']}"

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
            rsi14_curr = curr_row[rsi_col]
            atr14 = curr_row[atr_col]
            vol_sma = curr_row[vol_sma_col]

            close_p = float(curr_row["close"]) if "close" in curr_row else None
            open_p = float(curr_row["open"]) if "open" in curr_row else None
            vol = float(curr_row["volume"]) if "volume" in curr_row else None

            # Warm-up check: return HOLD if any required indicator is NaN/None
            if (
                close_p is None
                or open_p is None
                or vol is None
                or pd.isna(ema20)
                or pd.isna(ema50)
                or pd.isna(ema200)
                or pd.isna(rsi14_curr)
                or pd.isna(atr14)
                or pd.isna(vol_sma)
                or atr14 <= 0
                or vol_sma <= 0
            ):
                signals.append(self._create_hold_signal(symbol, trade_date, "Indicator warm-up period incomplete"))
                continue

            # Need at least 1 previous candle for RSI recovery check (RSI_{t-1}) and previous high (High_{t-1})
            if idx < 1:
                signals.append(
                    self._create_hold_signal(symbol, trade_date, "Insufficient history for previous candle confirmation")
                )
                continue

            prev_row = df.iloc[idx - 1]
            rsi14_prev = prev_row[rsi_col]
            prev_high = float(prev_row["high"]) if "high" in prev_row else None

            if pd.isna(rsi14_prev) or prev_high is None:
                signals.append(
                    self._create_hold_signal(symbol, trade_date, "Insufficient history for previous candle confirmation")
                )
                continue

            # ----------------------------------------------------
            # Evaluate Strategy Conditions
            # ----------------------------------------------------

            # 1. Trend Filter: Close > EMA200 AND EMA50 > EMA200
            cond1_trend = (close_p > ema200) and (ema50 > ema200)

            # 2. Oversold Condition & Recovery: Previous RSI14 < 40 AND Today's RSI14 > Previous RSI14
            rsi_oversold_threshold = float(self.parameters["rsi_oversold_max"])
            cond2_rsi_oversold_recovery = (rsi14_prev < rsi_oversold_threshold) and (rsi14_curr > rsi14_prev)

            # 3. Price Location: Close is within 3% of EMA20
            dist_pct = abs(close_p - ema20) / ema20 * 100.0
            cond3_location = dist_pct <= float(self.parameters["distance_from_ema20_percent"])

            # 4. Bullish Confirmation: Close > Open AND Close > Previous High
            cond4_bullish_confirm = (close_p > open_p) and (close_p > prev_high)

            # 5. Volume Confirmation: Volume >= 1.0 * Volume SMA20
            vol_multiplier = float(self.parameters["volume_multiplier"])
            vol_ratio = vol / vol_sma if vol_sma > 0 else 0.0
            cond5_volume = vol >= (vol_sma * vol_multiplier)

            all_conditions_pass = (
                cond1_trend
                and cond2_rsi_oversold_recovery
                and cond3_location
                and cond4_bullish_confirm
                and cond5_volume
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
                rsi_diff = rsi14_curr - rsi14_prev
                rsi_rec_comp = min(0.20, max(0.0, rsi_diff * 0.04))
                oversold_comp = min(0.15, max(0.0, (40.0 - rsi14_prev) * 0.015))
                prox_comp = min(0.10, max(0.0, 0.10 - dist_pct * 0.03))
                vol_comp = min(0.05, max(0.0, (vol_ratio - 1.0) * 0.10))
                score_val = round(min(0.99, max(0.50, 0.50 + rsi_rec_comp + oversold_comp + prox_comp + vol_comp)), 2)

                reason_str = (
                    f"EMA50 (₹{ema50:.2f}) > EMA200 (₹{ema200:.2f}), "
                    f"RSI recovered from {rsi14_prev:.1f} to {rsi14_curr:.1f}, "
                    f"close is {dist_pct:.1f}% from EMA20, "
                    f"bullish confirmation above previous high (Close {close_p:.2f} > PrevHigh {prev_high:.2f}), "
                    f"volume {vol_ratio:.1f}x average."
                )

                metadata_dict = {
                    "ema20": round(float(ema20), 2),
                    "ema50": round(float(ema50), 2),
                    "ema200": round(float(ema200), 2),
                    "rsi14": round(float(rsi14_curr), 2),
                    "previous_rsi14": round(float(rsi14_prev), 2),
                    "atr14": round(float(atr14), 2),
                    "volume_sma20": round(float(vol_sma), 2),
                    "volume_ratio": round(float(vol_ratio), 2),
                    "distance_from_ema20_pct": round(float(dist_pct), 2),
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
