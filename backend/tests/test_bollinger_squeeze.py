import numpy as np
import pandas as pd
import pytest

from backend.indicators.engine import calculate_indicators
from backend.strategies.base import BaseStrategy
from backend.strategies.bollinger_squeeze import BollingerSqueezeStrategy
from backend.strategies.models import SignalType, StrategySignal
from backend.strategies.registry import _GLOBAL_REGISTRY, get_strategy


def create_squeeze_dataset(
    num_candles: int = 150,
    base_price: float = 100.0,
    squeeze_length: int = 50,
    breakout: bool = True,
    high_volume: bool = True,
    high_rsi: bool = True,
    above_ema: bool = True,
) -> pd.DataFrame:
    """
    Constructs a deterministic synthetic OHLCV dataset for testing Bollinger Band Squeeze.
    """
    dates = pd.date_range(start="2025-01-01", periods=num_candles, freq="D")

    # Generate steady upward trend
    prices = [base_price + i * 0.2 for i in range(num_candles)]
    highs = [p + 0.5 for p in prices]
    lows = [p - 0.5 for p in prices]
    volumes = [1000] * num_candles

    df = pd.DataFrame(
        {
            "trade_date": dates.strftime("%Y-%m-%d"),
            "symbol": "TEST",
            "open": prices,
            "high": highs,
            "low": lows,
            "close": prices,
            "volume": volumes,
        }
    )

    # 1. Simulate tight squeeze phase before the final candle
    squeeze_start = num_candles - squeeze_length - 1
    squeeze_end = num_candles - 2
    for i in range(squeeze_start, squeeze_end + 1):
        flat_p = prices[squeeze_start] + (i % 2) * 0.02
        df.loc[i, "close"] = flat_p
        df.loc[i, "open"] = flat_p
        df.loc[i, "high"] = flat_p + 0.05
        df.loc[i, "low"] = flat_p - 0.05
        df.loc[i, "volume"] = 1000

    # Pre-calculate upper band on candle before last
    req_inds = [
        "ema_50",
        "bb_middle_20",
        "bb_upper_20",
        "bb_lower_20",
        "bb_width_20",
        "rsi_14",
        "atr_14",
        "volume_sma_20",
    ]
    df_temp = calculate_indicators(df, req_inds)
    last_idx = num_candles - 1
    prev_upper = float(df_temp.loc[last_idx - 1, "bb_upper_20"])
    prev_ema50 = float(df_temp.loc[last_idx, "ema_50"])

    if breakout:
        close_target = prev_upper + 2.0
    else:
        close_target = prev_upper - 1.0

    if not above_ema:
        close_target = min(close_target, prev_ema50 - 2.0)

    df.loc[last_idx, "close"] = close_target
    df.loc[last_idx, "open"] = close_target - 0.5
    df.loc[last_idx, "high"] = close_target + 0.5
    df.loc[last_idx, "low"] = close_target - 1.0

    if high_volume:
        df.loc[last_idx, "volume"] = 2500
    else:
        df.loc[last_idx, "volume"] = 800

    # Final indicator calculation
    df_ind = calculate_indicators(df, req_inds)

    if not high_rsi:
        df_ind.loc[last_idx, "rsi_14"] = 40.0
    elif high_rsi and df_ind.loc[last_idx, "rsi_14"] < 50.0:
        df_ind.loc[last_idx, "rsi_14"] = 65.0

    return df_ind


# --- Test A: Strategy Registration ---
def test_strategy_registration():
    strat = get_strategy("bollinger_squeeze")
    assert isinstance(strat, BollingerSqueezeStrategy)
    assert strat.name == "Bollinger Squeeze"
    assert strat.version == "1.0"
    assert "bollinger_squeeze" in _GLOBAL_REGISTRY.list_names()


# --- Test B: BUY Signal ---
def test_buy_signal_satisfied():
    df = create_squeeze_dataset(breakout=True, high_volume=True, high_rsi=True, above_ema=True)
    strat = BollingerSqueezeStrategy()
    signals = strat.generate_signals(df)

    assert len(signals) == len(df)
    last_signal = signals[-1]
    assert last_signal.signal == SignalType.BUY
    assert last_signal.entry_price > 0
    assert last_signal.stop_loss < last_signal.entry_price
    assert last_signal.target_price > last_signal.entry_price


# --- Test C: HOLD - No Squeeze ---
def test_hold_no_squeeze():
    # Volatile expanding price channel where pre-breakout band width is wide (not in squeeze quantile)
    num_candles = 150
    dates = pd.date_range(start="2025-01-01", periods=num_candles, freq="D")
    # Steady narrow prices first, then massive price expansion right before last candle
    prices = [100.0 + i * 0.1 for i in range(num_candles)]
    df = pd.DataFrame(
        {
            "trade_date": dates.strftime("%Y-%m-%d"),
            "symbol": "TEST",
            "open": prices,
            "high": [p + 0.5 for p in prices],
            "low": [p - 0.5 for p in prices],
            "close": prices,
            "volume": [2000] * num_candles,
        }
    )

    # Force candle idx-1 to have massive price expansion so bb_width_prev is wide
    last_idx = num_candles - 1
    df.loc[last_idx - 1, "high"] = prices[last_idx - 1] + 20.0
    df.loc[last_idx - 1, "low"] = prices[last_idx - 1] - 20.0
    df.loc[last_idx - 1, "close"] = prices[last_idx - 1] + 15.0

    df_ind = calculate_indicators(
        df,
        [
            "ema_50",
            "bb_middle_20",
            "bb_upper_20",
            "bb_lower_20",
            "bb_width_20",
            "rsi_14",
            "atr_14",
            "volume_sma_20",
        ],
    )

    # Force a final breakout close above previous upper band
    prev_upper = float(df_ind.loc[last_idx - 1, "bb_upper_20"])
    df_ind.loc[last_idx, "close"] = prev_upper + 5.0
    df_ind.loc[last_idx, "high"] = prev_upper + 6.0
    df_ind.loc[last_idx, "volume"] = 5000
    df_ind.loc[last_idx, "rsi_14"] = 65.0

    strat = BollingerSqueezeStrategy()
    signals = strat.generate_signals(df_ind)
    assert signals[-1].signal == SignalType.HOLD
    assert "Band width not in squeeze state" in signals[-1].reason


# --- Test D: HOLD - No Breakout ---
def test_hold_no_breakout():
    df = create_squeeze_dataset(breakout=False, high_volume=True, high_rsi=True, above_ema=True)
    strat = BollingerSqueezeStrategy()
    signals = strat.generate_signals(df)

    assert signals[-1].signal == SignalType.HOLD
    assert "Prev Upper Band" in signals[-1].reason


# --- Test E: HOLD - Weak Momentum (RSI < 50) ---
def test_hold_weak_momentum():
    df = create_squeeze_dataset(breakout=True, high_volume=True, high_rsi=False, above_ema=True)
    strat = BollingerSqueezeStrategy()
    signals = strat.generate_signals(df)

    assert signals[-1].signal == SignalType.HOLD
    assert "RSI14" in signals[-1].reason


# --- Test F: HOLD - Weak Volume ---
def test_hold_weak_volume():
    df = create_squeeze_dataset(breakout=True, high_volume=False, high_rsi=True, above_ema=True)
    strat = BollingerSqueezeStrategy()
    signals = strat.generate_signals(df)

    assert signals[-1].signal == SignalType.HOLD
    assert "Volume" in signals[-1].reason


# --- Test G: HOLD - Weak Trend (Close <= EMA50) ---
def test_hold_weak_trend():
    df = create_squeeze_dataset(breakout=True, high_volume=True, high_rsi=True, above_ema=False)
    strat = BollingerSqueezeStrategy()
    signals = strat.generate_signals(df)

    assert signals[-1].signal == SignalType.HOLD
    assert "EMA50" in signals[-1].reason


# --- Test H: Insufficient Data ---
def test_insufficient_data():
    df = pd.DataFrame(
        {
            "trade_date": ["2025-01-01", "2025-01-02"],
            "symbol": "SHORT",
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000, 1100],
        }
    )
    df_ind = calculate_indicators(
        df,
        [
            "ema_50",
            "bb_middle_20",
            "bb_upper_20",
            "bb_lower_20",
            "bb_width_20",
            "rsi_14",
            "atr_14",
            "volume_sma_20",
        ],
    )
    strat = BollingerSqueezeStrategy()
    signals = strat.generate_signals(df_ind)

    assert len(signals) == 2
    assert all(s.signal == SignalType.HOLD for s in signals)


# --- Test I: Edge Cases & Zero Values ---
def test_zero_volume_and_nan_edge_cases():
    df = pd.DataFrame(
        {
            "trade_date": ["2025-01-01"] * 30,
            "symbol": "ZERO",
            "open": [0.0] * 30,
            "high": [0.0] * 30,
            "low": [0.0] * 30,
            "close": [0.0] * 30,
            "volume": [0] * 30,
        }
    )
    df_ind = calculate_indicators(
        df,
        [
            "ema_50",
            "bb_middle_20",
            "bb_upper_20",
            "bb_lower_20",
            "bb_width_20",
            "rsi_14",
            "atr_14",
            "volume_sma_20",
        ],
    )
    strat = BollingerSqueezeStrategy()
    signals = strat.generate_signals(df_ind)

    assert len(signals) == 30
    assert all(s.signal == SignalType.HOLD for s in signals)


# --- Test J: Look-Ahead Bias Protection ---
def test_no_lookahead_bias():
    df1 = create_squeeze_dataset(num_candles=150, breakout=True)

    # df2 is identical to df1 up to index 149, but has future candles attached
    df2 = df1.copy()
    future_rows = pd.DataFrame(
        {
            "trade_date": ["2025-07-01", "2025-07-02"],
            "symbol": "TEST",
            "open": [999.0, 999.0],
            "high": [1000.0, 1000.0],
            "low": [998.0, 998.0],
            "close": [999.0, 999.0],
            "volume": [99999, 99999],
            "ema_50": [100.0, 100.0],
            "bb_middle_20": [100.0, 100.0],
            "bb_upper_20": [105.0, 105.0],
            "bb_lower_20": [95.0, 95.0],
            "bb_width_20": [0.10, 0.10],
            "rsi_14": [70.0, 70.0],
            "atr_14": [2.0, 2.0],
            "volume_sma_20": [1000, 1000],
        }
    )
    df2 = pd.concat([df2, future_rows], ignore_index=True)

    strat = BollingerSqueezeStrategy()
    signals1 = strat.generate_signals(df1)
    signals2 = strat.generate_signals(df2)

    # Signal evaluated at index 149 MUST be identical in both datasets
    sig1_eval = signals1[149]
    sig2_eval = signals2[149]

    assert sig1_eval.signal == sig2_eval.signal
    assert sig1_eval.entry_price == sig2_eval.entry_price
    assert sig1_eval.stop_loss == sig2_eval.stop_loss
    assert sig1_eval.target_price == sig2_eval.target_price


# --- Test K: Risk / Reward Ratios ---
def test_risk_reward_ratios():
    df = create_squeeze_dataset(breakout=True, high_volume=True, high_rsi=True, above_ema=True)
    strat = BollingerSqueezeStrategy()
    signals = strat.generate_signals(df)

    last_sig = signals[-1]
    assert last_sig.signal == SignalType.BUY

    risk = last_sig.entry_price - last_sig.stop_loss
    reward = last_sig.target_price - last_sig.entry_price
    rr = reward / risk

    assert risk > 0
    assert reward > 0
    assert round(rr, 2) == 2.0
