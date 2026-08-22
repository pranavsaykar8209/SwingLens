from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from .base import BaseStrategy
from .models import SignalType, StrategySignal
from .registry import register_strategy


@register_strategy
class MACDMomentumStrategy(BaseStrategy):
    """
    MACD Momentum Strategy v1.0

    A swing-trading momentum/trend-following strategy that enters long positions when:
    1. Stock is in a established bullish trend (EMA50 > EMA200, Close > EMA200, and Close > EMA20).
    2. MACD Line > Signal Line AND MACD Histogram > 0.
    3. MACD Histogram is strengthening (Current > Previous) or newly positive (Previous <= 0).
    4. Bullish confirmation candle (Close > Open and Close > Previous Day's High).
    5. Volume confirmation (Volume >= 1.2x 20-day Volume SMA).
    6. RSI14 between 50 and 70.
    """

    name: str = "MACD Momentum"
    version: str = "1.0"
    description: str = (
        "Swing trading momentum strategy entering when MACD histogram is positive "
        "and strengthening with EMA alignment, RSI, volume, and breakout confirmation."
    )
    timeframe: str = "1d"
    required_indicators: List[str] = [
        "ema_20",
        "ema_50",
        "ema_200",
        "macd",
        "macd_signal",
        "macd_histogram",
        "rsi_14",
        "atr_14",
        "volume_sma_20",
    ]
    default_parameters: Dict[str, Any] = {
        "ema_fast": 20,
        "ema_trend": 50,
        "ema_long": 200,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "rsi_max": 70.0,
        "volume_period": 20,
        "volume_multiplier": 1.2,
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
            req_cols = [
                ema_fast_col,
                ema_trend_col,
                ema_long_col,
                "macd",
                "macd_signal",
                "macd_histogram",
                rsi_col,
                atr_col,
                vol_sma_col,
            ]
            missing_cols = [c for c in req_cols if c not in curr_row]

            if missing_cols:
                signals.append(self._create_hold_signal(symbol, trade_date, "Missing indicator columns"))
                continue

            # Extract indicator values for current candle
            ema20 = curr_row[ema_fast_col]
            ema50 = curr_row[ema_trend_col]
            ema200 = curr_row[ema_long_col]
            macd_val = curr_row["macd"]
            macd_sig = curr_row["macd_signal"]
            macd_hist_curr = curr_row["macd_histogram"]
            rsi14 = curr_row[rsi_col]
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
                or pd.isna(macd_val)
                or pd.isna(macd_sig)
                or pd.isna(macd_hist_curr)
                or pd.isna(rsi14)
                or pd.isna(atr14)
                or pd.isna(vol_sma)
                or atr14 <= 0
                or vol_sma <= 0
            ):
                signals.append(self._create_hold_signal(symbol, trade_date, "Indicator warm-up period incomplete"))
                continue

            # Need at least 1 previous candle for momentum check (MACD_hist_{t-1}) and previous high (High_{t-1})
            if idx < 1:
                signals.append(
                    self._create_hold_signal(symbol, trade_date, "Insufficient history for previous candle confirmation")
                )
                continue

            prev_row = df.iloc[idx - 1]
            macd_hist_prev = prev_row.get("macd_histogram")
            prev_high = float(prev_row["high"]) if "high" in prev_row else None

            if macd_hist_prev is None or pd.isna(macd_hist_prev) or prev_high is None:
                signals.append(
                    self._create_hold_signal(symbol, trade_date, "Insufficient history for previous candle confirmation")
                )
                continue

            # ----------------------------------------------------
            # Evaluate Strategy Conditions
            # ----------------------------------------------------

            # 1. Trend Filter: EMA50 > EMA200 AND Close > EMA200 AND Close > EMA20
            cond1_trend = (ema50 > ema200) and (close_p > ema200) and (close_p > ema20)

            # 2. MACD Line > Signal Line AND MACD Histogram > 0
            cond2_macd_positive = (macd_val > macd_sig) and (macd_hist_curr > 0)

            # 3. MACD Momentum strengthening or newly positive
            cond3_macd_momentum = (macd_hist_prev <= 0) or (macd_hist_curr > macd_hist_prev)

            # 4. Bullish Confirmation: Close > Open AND Close > Previous High
            cond4_bullish_confirm = (close_p > open_p) and (close_p > prev_high)

            # 5. Volume Confirmation: Volume >= 1.2 * Volume SMA20
            vol_multiplier = float(self.parameters["volume_multiplier"])
            vol_ratio = vol / vol_sma if vol_sma > 0 else 0.0
            cond5_volume = vol >= (vol_sma * vol_multiplier)

            # 6. RSI Filter: 50 <= RSI14 <= 70
            rsi_min = float(self.parameters["rsi_min"])
            rsi_max = float(self.parameters["rsi_max"])
            cond6_rsi = rsi_min <= rsi14 <= rsi_max

            all_conditions_pass = (
                cond1_trend
                and cond2_macd_positive
                and cond3_macd_momentum
                and cond4_bullish_confirm
                and cond5_volume
                and cond6_rsi
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
                trend_pct = (close_p - ema200) / ema200 * 100.0
                trend_comp = min(0.10, max(0.0, trend_pct * 0.02))
                macd_dist = macd_val - macd_sig
                macd_comp = min(0.15, max(0.0, macd_dist * 0.10))
                hist_diff = macd_hist_curr - macd_hist_prev
                hist_comp = min(0.15, max(0.0, hist_diff * 0.20))
                vol_comp = min(0.05, max(0.0, (vol_ratio - vol_multiplier) * 0.10))
                rsi_comp = min(0.05, max(0.0, 0.05 - abs(rsi14 - 60.0) * 0.005))
                score_val = round(min(0.99, max(0.50, 0.50 + trend_comp + macd_comp + hist_comp + vol_comp + rsi_comp)), 2)

                hist_status = "strengthening" if macd_hist_curr > macd_hist_prev else "newly positive"
                reason_str = (
                    f"EMA50 (₹{ema50:.2f}) > EMA200 (₹{ema200:.2f}), price above EMA20, "
                    f"MACD ({macd_val:.2f} > {macd_sig:.2f}) bullish with histogram {hist_status} ({macd_hist_curr:.2f} > {macd_hist_prev:.2f}), "
                    f"RSI14={rsi14:.1f}, breakout above previous high (Close {close_p:.2f} > PrevHigh {prev_high:.2f}), "
                    f"volume {vol_ratio:.1f}x average."
                )

                metadata_dict = {
                    "ema20": round(float(ema20), 2),
                    "ema50": round(float(ema50), 2),
                    "ema200": round(float(ema200), 2),
                    "macd": round(float(macd_val), 2),
                    "macd_signal": round(float(macd_sig), 2),
                    "macd_histogram": round(float(macd_hist_curr), 2),
                    "previous_macd_histogram": round(float(macd_hist_prev), 2),
                    "rsi14": round(float(rsi14), 2),
                    "atr14": round(float(atr14), 2),
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
