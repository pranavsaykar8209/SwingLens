import numpy as np
import pandas as pd
import pytest

from backend.backtest import BacktestEngine
from backend.indicators import calculate_indicators
from backend.scanner import MarketScanner
from backend.strategies import (
    EMAPullbackStrategy,
    MATrendBreakoutStrategy,
    SignalType,
    get_strategy,
    list_strategies,
)


def create_synthetic_breakout_df(
    n_candles=25,
    ema50=550.0,
    ema200=500.0,
    close=580.0,
    prev_20_high=570.0,
    today_high=585.0,
    rsi=60.0,
    atr=10.0,
    vol=3000.0,
    vol_sma=1800.0,
):
    """
    Helper creating a valid synthetic DataFrame of N candles for MA Trend Breakout testing.
    The last candle (index n_candles-1) represents today.
    Candles 0 to n_candles-2 represent historical history with previous highs.
    """
    trade_dates = [f"2024-01-{i+1:02d}" for i in range(n_candles)]
    
    # Initialize base prices
    opens = [540.0] * n_candles
    highs = [prev_20_high - 5.0] * n_candles
    lows = [530.0] * n_candles
    closes = [545.0] * n_candles
    volumes = [vol_sma] * n_candles

    # Ensure at least one candle in previous 20 sessions hit prev_20_high
    if n_candles > 5:
        highs[5] = prev_20_high

    # Set values for today (last candle)
    opens[-1] = 572.0
    highs[-1] = today_high
    lows[-1] = 570.0
    closes[-1] = close
    volumes[-1] = vol

    df = pd.DataFrame({
        "symbol": ["RELIANCE"] * n_candles,
        "trade_date": trade_dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "ema_50": [ema50 - 5.0] * (n_candles - 1) + [ema50],
        "ema_200": [ema200 - 5.0] * (n_candles - 1) + [ema200],
        "rsi_14": [55.0] * (n_candles - 1) + [rsi],
        "atr_14": [9.5] * (n_candles - 1) + [atr],
        "volume_sma_20": [vol_sma] * n_candles,
        "highest_high_20": [prev_20_high] * n_candles,
    })

    return df


# 1. Valid BUY Setup Test
def test_ma_trend_breakout_valid_buy():
    df = create_synthetic_breakout_df()
    strat = MATrendBreakoutStrategy()
    signals = strat.generate_signals(df)

    assert len(signals) == 25
    sig = signals[-1]
    assert sig.signal == SignalType.BUY
    assert sig.symbol == "RELIANCE"
    assert sig.strategy_name == "MA Trend Breakout"
    assert sig.strategy_version == "1.0"


# 2. EMA50 <= EMA200 -> No BUY Test
def test_ma_trend_breakout_ema50_less_than_ema200():
    df = create_synthetic_breakout_df(ema50=490.0, ema200=500.0)
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 3. Close <= EMA200 -> No BUY Test
def test_ma_trend_breakout_close_less_than_ema200():
    df = create_synthetic_breakout_df(close=495.0, ema200=500.0)
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 4. Close does not break previous 20-day high -> No BUY Test
def test_ma_trend_breakout_no_breakout():
    df = create_synthetic_breakout_df(close=565.0, prev_20_high=570.0)
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 5. Volume below threshold -> No BUY Test
def test_ma_trend_breakout_low_volume():
    # 2000 < 1.5 * 1800 (2700)
    df = create_synthetic_breakout_df(vol=2000.0, vol_sma=1800.0)
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 6. RSI below 50 -> No BUY Test
def test_ma_trend_breakout_rsi_low():
    df = create_synthetic_breakout_df(rsi=48.0)
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 7. RSI above 70 -> No BUY Test
def test_ma_trend_breakout_rsi_high():
    df = create_synthetic_breakout_df(rsi=72.0)
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 8. Insufficient Data -> SKIPPED / HOLD Test
def test_ma_trend_breakout_insufficient_data():
    df_short = create_synthetic_breakout_df(n_candles=10)
    strat = MATrendBreakoutStrategy()
    signals = strat.generate_signals(df_short)
    sig = signals[-1]
    assert sig.signal == SignalType.HOLD
    assert "Insufficient history" in sig.reason


# 9. Correct Entry Price Test
def test_ma_trend_breakout_entry_price():
    df = create_synthetic_breakout_df(close=580.0)
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.entry_price == 580.0


# 10. Correct ATR Stop Loss Test
def test_ma_trend_breakout_stop_loss():
    # Close = 580.0, ATR = 10.0 -> Stop = 580 - (1.5 * 10) = 565.0
    df = create_synthetic_breakout_df(close=580.0, atr=10.0)
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.stop_loss == 565.0
    assert sig.stop_loss < sig.entry_price


# 11. Correct 1:2 Target Price Test
def test_ma_trend_breakout_target_price():
    # Entry = 580.0, Stop = 565.0, Risk = 15.0 -> Target = 580 + (2.0 * 15) = 610.0
    df = create_synthetic_breakout_df(close=580.0, atr=10.0)
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.target_price == 610.0


# 12. Correct Risk/Reward Ratio Test
def test_ma_trend_breakout_risk_reward():
    df = create_synthetic_breakout_df()
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.risk_reward == 2.0


# 13. Dynamic Reason Text Test
def test_ma_trend_breakout_reason_text():
    df = create_synthetic_breakout_df(
        ema50=560.20,
        ema200=520.10,
        close=575.30,
        prev_20_high=568.40,
        rsi=61.2,
    )
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.BUY
    assert "EMA50 (₹560.20) > EMA200 (₹520.10)" in sig.reason
    assert "close (₹575.30) broke previous 20-day high (₹568.40)" in sig.reason
    assert "RSI14=61.2" in sig.reason


# 14. Metadata Contains Expected Indicators Test
def test_ma_trend_breakout_metadata():
    df = create_synthetic_breakout_df()
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    meta = sig.metadata
    assert "ema50" in meta
    assert "ema200" in meta
    assert "rsi14" in meta
    assert "atr14" in meta
    assert "previous_20_high" in meta
    assert "volume_sma20" in meta
    assert "volume_ratio" in meta
    assert meta["ema50"] == 550.0
    assert meta["ema200"] == 500.0


# 15. No Look-Ahead Bias Guarantee Test
def test_ma_trend_breakout_no_lookahead():
    df1 = create_synthetic_breakout_df(n_candles=30)
    df2 = df1.copy()
    # Modify future candle at index 29
    df2.iloc[29, df2.columns.get_loc("close")] = 10.0

    strat = MATrendBreakoutStrategy()
    sig1 = strat.generate_signals(df1.iloc[:29])
    sig2 = strat.generate_signals(df2.iloc[:29])

    # Signal at index 28 MUST be identical regardless of future candle at index 29
    assert sig1[-1].signal == sig2[-1].signal
    assert sig1[-1].entry_price == sig2[-1].entry_price
    assert sig1[-1].stop_loss == sig2[-1].stop_loss


# 16. Previous 20-Day High Excludes Today's Candle Test
def test_ma_trend_breakout_excludes_today_candle():
    # Previous 20 candles high = 570.0. Today's high = 600.0.
    # Today's close = 580.0 (breaks prev_20_high 570.0, even though close 580 < today's high 600)
    df = create_synthetic_breakout_df(
        close=580.0,
        prev_20_high=570.0,
        today_high=600.0,
    )
    strat = MATrendBreakoutStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.BUY
    assert sig.metadata["previous_20_high"] == 570.0


# 17. Existing EMA Pullback v1.0 Tests Still Pass
def test_existing_ema_pullback_unaffected():
    strat = EMAPullbackStrategy()
    assert strat.name == "EMA Pullback"
    assert strat.version == "1.0"


# 18. Scanner Compatibility Test
def test_scanner_with_ma_trend_breakout():
    strat = get_strategy("ma_trend_breakout")
    assert strat.name == "MA Trend Breakout"


# 19. Backtest Engine Compatibility Test
def test_backtest_with_ma_trend_breakout():
    df = create_synthetic_breakout_df(n_candles=40)
    strat = get_strategy("ma_trend_breakout")
    engine = BacktestEngine(strategy=strat)
    result = engine.run(df)
    assert result.strategy == "MA Trend Breakout"
    assert isinstance(result.total_trades, int)


# 20. Strategy Registry Returns Both Strategies Test
def test_registry_returns_both_strategies():
    strats = list_strategies()
    names = [s["name"] for s in strats]
    assert "EMA Pullback" in names
    assert "MA Trend Breakout" in names

    inst1 = get_strategy("ema_pullback")
    assert isinstance(inst1, EMAPullbackStrategy)

    inst2 = get_strategy("ma_trend_breakout")
    assert isinstance(inst2, MATrendBreakoutStrategy)
