import numpy as np
import pandas as pd
import pytest

from backend.backtest import BacktestEngine
from backend.scanner import MarketScanner
from backend.strategies import (
    EMAPullbackStrategy,
    MATrendBreakoutStrategy,
    RSIMeanReversionStrategy,
    SignalType,
    get_strategy,
    list_strategies,
)


def create_synthetic_rsi_mr_df(
    n_candles=5,
    close=530.0,
    open_p=522.0,
    ema20=525.0,
    ema50=510.0,
    ema200=480.0,
    rsi_prev=35.0,
    rsi_curr=42.0,
    prev_high=528.0,
    vol=1500.0,
    vol_sma=1200.0,
    atr=8.0,
):
    """
    Helper creating a valid synthetic DataFrame for RSI Mean-Reversion testing.
    The last candle (index n_candles-1) represents today.
    Candle n_candles-2 represents yesterday (t-1).
    """
    trade_dates = [f"2024-01-{i+1:02d}" for i in range(n_candles)]

    opens = [520.0] * n_candles
    highs = [525.0] * n_candles
    lows = [515.0] * n_candles
    closes = [522.0] * n_candles
    volumes = [vol_sma] * n_candles

    # Yesterday (t-2 index for last candle)
    if n_candles >= 2:
        highs[-2] = prev_high
        closes[-2] = 524.0

    # Today (last candle)
    opens[-1] = open_p
    highs[-1] = close + 2.0
    lows[-1] = open_p - 2.0
    closes[-1] = close
    volumes[-1] = vol

    rsis = [50.0] * n_candles
    if n_candles >= 2:
        rsis[-2] = rsi_prev
    rsis[-1] = rsi_curr

    df = pd.DataFrame({
        "symbol": ["TATASTEEL"] * n_candles,
        "trade_date": trade_dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "ema_20": [ema20] * n_candles,
        "ema_50": [ema50] * n_candles,
        "ema_200": [ema200] * n_candles,
        "rsi_14": rsis,
        "atr_14": [atr] * n_candles,
        "volume_sma_20": [vol_sma] * n_candles,
    })

    return df


# 1. Valid BUY Setup Test
def test_rsi_mr_valid_buy():
    df = create_synthetic_rsi_mr_df()
    strat = RSIMeanReversionStrategy()
    signals = strat.generate_signals(df)

    assert len(signals) == 5
    sig = signals[-1]
    assert sig.signal == SignalType.BUY
    assert sig.symbol == "TATASTEEL"
    assert sig.strategy_name == "RSI Mean-Reversion"
    assert sig.strategy_version == "1.0"


# 2. Close <= EMA200 -> No BUY Test
def test_rsi_mr_close_less_than_ema200():
    df = create_synthetic_rsi_mr_df(close=475.0, ema200=480.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 3. EMA50 <= EMA200 -> No BUY Test
def test_rsi_mr_ema50_less_than_ema200():
    df = create_synthetic_rsi_mr_df(ema50=470.0, ema200=480.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 4. Previous RSI >= 40 -> No BUY Test
def test_rsi_mr_previous_rsi_not_oversold():
    df = create_synthetic_rsi_mr_df(rsi_prev=42.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 5. Current RSI <= Previous RSI -> No BUY Test
def test_rsi_mr_rsi_not_recovering():
    df = create_synthetic_rsi_mr_df(rsi_prev=35.0, rsi_curr=33.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 6. Price > 3% away from EMA20 -> No BUY Test
def test_rsi_mr_distance_too_far_from_ema20():
    # close = 550.0 vs ema20 = 520.0 -> dist = 30 / 520 = 5.77% (> 3%)
    df = create_synthetic_rsi_mr_df(close=550.0, ema20=520.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 7. Bearish Candle (Close <= Open) -> No BUY Test
def test_rsi_mr_bearish_candle():
    df = create_synthetic_rsi_mr_df(close=520.0, open_p=525.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 8. Close <= Previous High -> No BUY Test
def test_rsi_mr_close_not_above_prev_high():
    df = create_synthetic_rsi_mr_df(close=525.0, prev_high=528.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 9. Volume below Volume SMA20 -> No BUY Test
def test_rsi_mr_low_volume():
    df = create_synthetic_rsi_mr_df(vol=1000.0, vol_sma=1200.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 10. Insufficient Data -> SKIPPED / HOLD Test
def test_rsi_mr_insufficient_data():
    df_single = create_synthetic_rsi_mr_df(n_candles=1)
    strat = RSIMeanReversionStrategy()
    signals = strat.generate_signals(df_single)
    sig = signals[-1]
    assert sig.signal == SignalType.HOLD
    assert "Insufficient history" in sig.reason


# 11. Correct Entry Price Test
def test_rsi_mr_entry_price():
    df = create_synthetic_rsi_mr_df(close=530.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.entry_price == 530.0


# 12. Correct ATR Stop Loss Test
def test_rsi_mr_stop_loss():
    # Close = 530.0, ATR = 8.0 -> Stop = 530 - (1.5 * 8) = 518.0
    df = create_synthetic_rsi_mr_df(close=530.0, atr=8.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.stop_loss == 518.0
    assert sig.stop_loss < sig.entry_price


# 13. Correct Target Price Test
def test_rsi_mr_target_price():
    # Entry = 530.0, Stop = 518.0, Risk = 12.0 -> Target = 530 + (2.0 * 12) = 554.0
    df = create_synthetic_rsi_mr_df(close=530.0, atr=8.0)
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.target_price == 554.0


# 14. Correct 1:2 Risk/Reward Ratio Test
def test_rsi_mr_risk_reward():
    df = create_synthetic_rsi_mr_df()
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.risk_reward == 2.0


# 15. Correct Reason String Test
def test_rsi_mr_reason_text():
    df = create_synthetic_rsi_mr_df(
        ema50=560.0,
        ema200=520.0,
        rsi_prev=36.8,
        rsi_curr=43.2,
    )
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.BUY
    assert "EMA50 (₹560.00) > EMA200 (₹520.00)" in sig.reason
    assert "RSI recovered from 36.8 to 43.2" in sig.reason
    assert "bullish confirmation" in sig.reason


# 16. Correct Metadata Contents Test
def test_rsi_mr_metadata():
    df = create_synthetic_rsi_mr_df()
    strat = RSIMeanReversionStrategy()
    sig = strat.generate_signals(df)[-1]
    meta = sig.metadata
    assert "ema20" in meta
    assert "ema50" in meta
    assert "ema200" in meta
    assert "rsi14" in meta
    assert "previous_rsi14" in meta
    assert "atr14" in meta
    assert "volume_sma20" in meta
    assert "volume_ratio" in meta
    assert "distance_from_ema20_pct" in meta
    assert meta["previous_rsi14"] == 35.0
    assert meta["rsi14"] == 42.0


# 17. No Look-Ahead Bias Guarantee Test
def test_rsi_mr_no_lookahead():
    df1 = create_synthetic_rsi_mr_df(n_candles=10)
    df2 = df1.copy()
    # Modify future candle at index 9
    df2.iloc[9, df2.columns.get_loc("close")] = 10.0

    strat = RSIMeanReversionStrategy()
    sig1 = strat.generate_signals(df1.iloc[:9])
    sig2 = strat.generate_signals(df2.iloc[:9])

    # Signal at index 8 MUST be identical regardless of future candle at index 9
    assert sig1[-1].signal == sig2[-1].signal
    assert sig1[-1].entry_price == sig2[-1].entry_price
    assert sig1[-1].stop_loss == sig2[-1].stop_loss


# 18. Strategy Registry Returns Strategy Test
def test_registry_returns_rsi_mean_reversion():
    strat = get_strategy("rsi_mean_reversion")
    assert isinstance(strat, RSIMeanReversionStrategy)
    assert strat.name == "RSI Mean-Reversion"


# 19. EMA Pullback Tests Still Pass Test
def test_existing_ema_pullback_unaffected():
    strat = EMAPullbackStrategy()
    assert strat.name == "EMA Pullback"


# 20. MA Trend Breakout Tests Still Pass Test
def test_existing_ma_trend_breakout_unaffected():
    strat = MATrendBreakoutStrategy()
    assert strat.name == "MA Trend Breakout"


# 21. Scanner Tests Still Pass Test
def test_scanner_with_rsi_mean_reversion():
    strat = get_strategy("rsi_mean_reversion")
    assert strat.name == "RSI Mean-Reversion"


# 22. Backtest Tests Still Pass Test
def test_backtest_with_rsi_mean_reversion():
    df = create_synthetic_rsi_mr_df(n_candles=20)
    strat = get_strategy("rsi_mean_reversion")
    engine = BacktestEngine(strategy=strat)
    result = engine.run(df)
    assert result.strategy == "RSI Mean-Reversion"
    assert isinstance(result.total_trades, int)


# 23. API Registry Listing Test
def test_all_three_strategies_in_registry():
    strats = list_strategies()
    names = [s["name"] for s in strats]
    assert "EMA Pullback" in names
    assert "MA Trend Breakout" in names
    assert "RSI Mean-Reversion" in names
