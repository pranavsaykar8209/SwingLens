import numpy as np
import pandas as pd
import pytest

from backend.indicators import calculate_indicators
from backend.strategies import EMAPullbackStrategy, SignalType


def create_synthetic_dataframe(
    ema20=240.0,
    ema50=230.0,
    ema200=200.0,
    close=242.0,
    prev_high=238.0,
    rsi=58.0,
    atr=5.0,
    vol=2000.0,
    vol_sma=1500.0,
):
    """
    Helper creating a valid 2-candle DataFrame for EMA Pullback testing.
    """
    return pd.DataFrame({
        "symbol": ["ABB", "ABB"],
        "trade_date": ["2024-01-01", "2024-01-02"],
        "open": [235.0, 239.0],
        "high": [prev_high, close + 2.0],  # Candle 0 high = prev_high
        "low": [230.0, 237.0],
        "close": [236.0, close],
        "volume": [1500.0, vol],
        "ema_20": [238.0, ema20],
        "ema_50": [228.0, ema50],
        "ema_200": [198.0, ema200],
        "rsi_14": [55.0, rsi],
        "atr_14": [4.8, atr],
        "volume_sma_20": [1400.0, vol_sma],
    })


# 1. All Conditions Pass -> BUY Signal
def test_ema_pullback_all_pass():
    df = create_synthetic_dataframe()
    strat = EMAPullbackStrategy()
    signals = strat.generate_signals(df)

    assert len(signals) == 2
    assert signals[0].signal == SignalType.HOLD
    sig = signals[1]
    assert sig.signal == SignalType.BUY
    assert sig.entry_price == 242.0
    # Stop loss = 242 - (1.5 * 5.0) = 234.5
    assert sig.stop_loss == 234.5
    # Target = 242 + 2.0 * (242 - 234.5) = 242 + 15 = 257.0
    assert sig.target_price == 257.0


# 2. Condition 1 Fail: EMA20 <= EMA50
def test_ema_pullback_cond1_fail():
    df = create_synthetic_dataframe(ema20=225.0, ema50=230.0)
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD


# 3. Condition 2 Fail: EMA50 <= EMA200
def test_ema_pullback_cond2_fail():
    df = create_synthetic_dataframe(ema50=195.0, ema200=200.0)
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD


# 4. Condition 3 Fail: Close <= EMA200
def test_ema_pullback_cond3_fail():
    df = create_synthetic_dataframe(close=195.0, ema200=200.0)
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD


# 5. Condition 4 Fail: Pullback Distance > 2%
def test_ema_pullback_cond4_fail():
    # close = 250.0 vs ema20 = 240.0 -> dist = 10 / 240 = 4.16% (> 2%)
    df = create_synthetic_dataframe(close=250.0, ema20=240.0)
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD


# 6. Condition 5 Fail: RSI < 50
def test_ema_pullback_cond5_rsi_low_fail():
    df = create_synthetic_dataframe(rsi=48.0)
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD


# 7. Condition 5 Fail: RSI > 65
def test_ema_pullback_cond5_rsi_high_fail():
    df = create_synthetic_dataframe(rsi=68.0)
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD


# 8. Condition 6 Fail: Bullish Confirmation (Close <= prev_high)
def test_ema_pullback_cond6_confirm_fail():
    df = create_synthetic_dataframe(close=237.0, prev_high=238.0)
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD


# 9. Condition 7 Fail: Volume < Volume_SMA20
def test_ema_pullback_cond7_volume_fail():
    df = create_synthetic_dataframe(vol=1200.0, vol_sma=1500.0)
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD


# 10. Condition 8 Fail: ATR NaN / Non-positive
def test_ema_pullback_cond8_atr_fail():
    df = create_synthetic_dataframe(atr=0.0)
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD


# 11. Custom Parameter Overrides Test
def test_ema_pullback_custom_parameters():
    df = create_synthetic_dataframe(rsi=45.0)  # Fails default min rsi (50)
    strat = EMAPullbackStrategy(parameters={"rsi_min": 40.0})
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.BUY


# 12. Warm-Up Period (NaN Indicators) Handling
def test_ema_pullback_warmup_nan():
    df = create_synthetic_dataframe()
    df.loc[1, "ema_200"] = np.nan
    strat = EMAPullbackStrategy()
    sig = strat.generate_signals(df)[1]
    assert sig.signal == SignalType.HOLD
    assert "warm-up" in sig.reason.lower()


# 13. No-Lookahead Guarantee
def test_ema_pullback_no_lookahead():
    df1 = pd.DataFrame({
        "symbol": ["ABB"] * 3,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [235.0, 239.0, 245.0],
        "high": [238.0, 244.0, 250.0],
        "low": [230.0, 237.0, 240.0],
        "close": [236.0, 242.0, 248.0],
        "volume": [1500.0, 2000.0, 2100.0],
        "ema_20": [238.0, 240.0, 242.0],
        "ema_50": [228.0, 230.0, 232.0],
        "ema_200": [198.0, 200.0, 202.0],
        "rsi_14": [55.0, 58.0, 60.0],
        "atr_14": [4.8, 5.0, 5.2],
        "volume_sma_20": [1400.0, 1500.0, 1550.0],
    })

    df2 = df1.copy()
    df2.iloc[2, df2.columns.get_loc("close")] = 10.0  # Future candle 2 altered

    strat = EMAPullbackStrategy()
    sig1 = strat.generate_signals(df1)
    sig2 = strat.generate_signals(df2)

    # Candle 1 signal must be IDENTICAL between both datasets
    assert sig1[1].signal == sig2[1].signal == SignalType.BUY
    assert sig1[1].stop_loss == sig2[1].stop_loss
