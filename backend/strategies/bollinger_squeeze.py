from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from .base import BaseStrategy
from .models import SignalType, StrategySignal
from .registry import register_strategy


@register_strategy
class BollingerSqueezeStrategy(BaseStrategy):
    """
    Bollinger Band Squeeze Strategy v1.0

    A swing-trading strategy that enters long positions when:
    1. Stock is in an established bullish trend (Close > EMA50).
    2. Bollinger Band Width is in a compressed squeeze state (<= 120-day rolling 20th percentile).
    3. Price breaks out above the PREVIOUS day's Upper Bollinger Band (Close > UpperBand_{t-1}).
    4. Momentum confirmation (RSI14 >= 50).
    5. Volume confirmation (Volume > 20-day Volume SMA).
    6. ATR-based risk/reward setup (Stop Loss = Entry - 1.5x ATR, Target = Entry + 3.0x ATR, 2.0 R:R).
    """

    name: str = "Bollinger Squeeze"
    version: str = "1.0"
    description: str = (
        "Swing trading squeeze strategy entering when Bollinger Bands compress "
        "(squeeze lookback percentile) and break out above previous upper band with "
        "EMA trend, RSI, and volume confirmation."
    )
    timeframe: str = "1d"
    required_indicators: List[str] = [
        "ema_50",
        "bb_middle_20",
        "bb_upper_20",
        "bb_lower_20",
        "bb_width_20",
        "rsi_14",
        "atr_14",
        "volume_sma_20",
    ]
    default_parameters: Dict[str, Any] = {
        "ema_trend": 50,
        "bb_period": 20,
        "bb_std": 2.0,
        "squeeze_lookback": 120,
        "squeeze_percentile": 0.20,
        "rsi_period": 14,
        "rsi_min": 50.0,
        "volume_period": 20,
        "volume_multiplier": 1.0,
        "atr_period": 14,
        "atr_stop_multiplier": 1.5,
        "atr_target_multiplier": 3.0,
        "reward_risk_ratio": 2.0,
    }

    def generate_signals(self, df: pd.DataFrame) -> List[StrategySignal]:
        signals: List[StrategySignal] = []
        if df.empty:
            return signals

        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"

        ema_trend_col = f"ema_{self.parameters['ema_trend']}"
        bb_period = self.parameters["bb_period"]
        bb_upper_col = f"bb_upper_{bb_period}"
        bb_middle_col = f"bb_middle_{bb_period}"
        bb_lower_col = f"bb_lower_{bb_period}"
        bb_width_col = f"bb_width_{bb_period}"
        rsi_col = f"rsi_{self.parameters['rsi_period']}"
        atr_col = f"atr_{self.parameters['atr_period']}"
        vol_sma_col = f"volume_sma_{self.parameters['volume_period']}"

        squeeze_lookback = int(self.parameters["squeeze_lookback"])
        squeeze_percentile = float(self.parameters["squeeze_percentile"])

        for idx in range(len(df)):
            curr_row = df.iloc[idx]
            trade_date = str(curr_row["trade_date"]) if "trade_date" in curr_row else str(idx)

            req_cols = [
                ema_trend_col,
                bb_upper_col,
                bb_middle_col,
                bb_lower_col,
                bb_width_col,
                rsi_col,
                atr_col,
                vol_sma_col,
            ]
            missing_cols = [c for c in req_cols if c not in curr_row]

            if missing_cols:
                signals.append(self._create_hold_signal(symbol, trade_date, "Missing indicator columns"))
                continue

            ema50 = curr_row[ema_trend_col]
            bb_upper_curr = curr_row[bb_upper_col]
            bb_middle_curr = curr_row[bb_middle_col]
            bb_lower_curr = curr_row[bb_lower_col]
            bb_width_curr = curr_row[bb_width_col]
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
                or pd.isna(ema50)
                or pd.isna(bb_upper_curr)
                or pd.isna(bb_middle_curr)
                or pd.isna(bb_lower_curr)
                or pd.isna(bb_width_curr)
                or pd.isna(rsi14)
                or pd.isna(atr14)
                or pd.isna(vol_sma)
                or atr14 <= 0
                or vol_sma <= 0
            ):
                signals.append(self._create_hold_signal(symbol, trade_date, "Indicator warm-up period incomplete"))
                continue

            # Require at least 1 previous candle for previous upper band comparison
            if idx < 1:
                signals.append(
                    self._create_hold_signal(symbol, trade_date, "Insufficient history for previous upper band breakout")
                )
                continue

            prev_row = df.iloc[idx - 1]
            bb_upper_prev = prev_row.get(bb_upper_col)
            if bb_upper_prev is None or pd.isna(bb_upper_prev):
                signals.append(
                    self._create_hold_signal(symbol, trade_date, "Insufficient history for previous upper band breakout")
                )
                continue

            # ----------------------------------------------------
            # Evaluate Strategy Conditions
            # ----------------------------------------------------

            # 1. Established Trend: Close > EMA50
            cond1_trend = close_p > ema50

            # 2. Squeeze Condition: Pre-breakout band width (candle idx-1) <= rolling lookback percentile threshold
            window_start = max(0, idx - squeeze_lookback)
            bw_series = df[bb_width_col].iloc[window_start:idx].dropna()

            if len(bw_series) < 5:
                cond2_squeeze = False
                squeeze_threshold = float("nan")
            else:
                squeeze_threshold = float(bw_series.quantile(squeeze_percentile))
                bb_width_prev = float(df[bb_width_col].iloc[idx - 1])
                cond2_squeeze = bb_width_prev <= squeeze_threshold

            # 3. Upside Breakout: Close > Previous Upper Bollinger Band
            cond3_breakout = close_p > float(bb_upper_prev)

            # 4. Momentum Confirmation: RSI14 >= rsi_min
            rsi_min = float(self.parameters["rsi_min"])
            cond4_rsi = rsi14 >= rsi_min

            # 5. Volume Confirmation: Volume > Volume SMA20
            vol_multiplier = float(self.parameters["volume_multiplier"])
            vol_ratio = vol / vol_sma if vol_sma > 0 else 0.0
            cond5_volume = vol > (vol_sma * vol_multiplier)

            all_conditions_pass = (
                cond1_trend
                and cond2_squeeze
                and cond3_breakout
                and cond4_rsi
                and cond5_volume
            )

            if all_conditions_pass:
                atr_stop_mult = float(self.parameters["atr_stop_multiplier"])
                atr_target_mult = float(self.parameters["atr_target_multiplier"])
                rr_ratio = float(self.parameters["reward_risk_ratio"])

                stop_loss = close_p - (atr14 * atr_stop_mult)
                if stop_loss >= close_p:
                    signals.append(self._create_hold_signal(symbol, trade_date, "Invalid stop-loss level"))
                    continue

                risk = close_p - stop_loss
                target_price = close_p + (risk * rr_ratio)

                reason_str = (
                    f"Close (₹{close_p:.2f}) > EMA50 (₹{ema50:.2f}), "
                    f"Bollinger Band Squeeze active (BandWidth {bb_width_curr:.4f} <= {squeeze_threshold:.4f}), "
                    f"upside breakout above previous upper band (Close {close_p:.2f} > PrevUpper {bb_upper_prev:.2f}), "
                    f"RSI14={rsi14:.1f} >= {rsi_min}, volume {vol_ratio:.1f}x average."
                )

                metadata_dict = {
                    "ema50": round(float(ema50), 2),
                    "bb_middle": round(float(bb_middle_curr), 2),
                    "bb_upper_curr": round(float(bb_upper_curr), 2),
                    "bb_upper_prev": round(float(bb_upper_prev), 2),
                    "bb_lower": round(float(bb_lower_curr), 2),
                    "bb_width": round(float(bb_width_curr), 4),
                    "squeeze_threshold": round(float(squeeze_threshold), 4),
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
                        score=0.85,
                        reason=reason_str,
                        metadata=metadata_dict,
                    )
                )
            else:
                reasons = []
                if not cond1_trend:
                    reasons.append(f"Close ({close_p:.2f}) <= EMA50 ({ema50:.2f})")
                if not cond2_squeeze:
                    reasons.append("Band width not in squeeze state")
                if not cond3_breakout:
                    reasons.append(f"Close ({close_p:.2f}) <= Prev Upper Band ({bb_upper_prev:.2f})")
                if not cond4_rsi:
                    reasons.append(f"RSI14 ({rsi14:.1f}) < {rsi_min}")
                if not cond5_volume:
                    reasons.append(f"Volume ({vol}) <= SMA volume ({vol_sma:.0f})")

                reason_summary = "Setup conditions not satisfied: " + "; ".join(reasons)
                signals.append(
                    StrategySignal(
                        symbol=symbol,
                        strategy_name=self.name,
                        strategy_version=self.version,
                        signal=SignalType.HOLD,
                        signal_date=trade_date,
                        entry_price=round(close_p, 2),
                        reason=reason_summary,
                    )
                )

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
