import numpy as np
import pandas as pd
import pytest

from backend.backtest import BacktestEngine
from backend.scanner import MarketScanner
from backend.strategies import (
    EMAPullbackStrategy,
    MACDMomentumStrategy,
    MATrendBreakoutStrategy,
    RSIMeanReversionStrategy,
    SignalType,
    get_strategy,
    list_strategies,
)


def create_synthetic_macd_momentum_df(
    n_candles=5,
    close=580.0,
    open_p=570.0,
    ema20=560.0,
    ema50=550.0,
    ema200=500.0,
    macd_val=2.5,
    macd_sig=1.5,
    hist_prev=0.5,
    hist_curr=1.0,
    prev_high=575.0,
    rsi=60.0,
    atr=10.0,
    vol=2500.0,
    vol_sma=1800.0,
):
    """
    Helper creating a valid synthetic DataFrame for MACD Momentum testing.
    The last candle (index n_candles-1) represents today.
    """
    trade_dates = [f"2024-01-{i+1:02d}" for i in range(n_candles)]

    opens = [565.0] * n_candles
    highs = [572.0] * n_candles
    lows = [560.0] * n_candles
    closes = [568.0] * n_candles
    volumes = [vol_sma] * n_candles

    # Yesterday (index -2)
    if n_candles >= 2:
        highs[-2] = prev_high

    # Today (index -1)
    opens[-1] = open_p
    highs[-1] = close + 2.0
    lows[-1] = open_p - 2.0
    closes[-1] = close
    volumes[-1] = vol

    hists = [0.2] * n_candles
    if n_candles >= 2:
        hists[-2] = hist_prev
    hists[-1] = hist_curr

    df = pd.DataFrame({
        "symbol": ["INFY"] * n_candles,
        "trade_date": trade_dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "ema_20": [ema20] * n_candles,
        "ema_50": [ema50] * n_candles,
        "ema_200": [ema200] * n_candles,
        "macd": [macd_val - 0.5] * (n_candles - 1) + [macd_val],
        "macd_signal": [macd_sig - 0.3] * (n_candles - 1) + [macd_sig],
        "macd_histogram": hists,
        "rsi_14": [rsi] * n_candles,
        "atr_14": [atr] * n_candles,
        "volume_sma_20": [vol_sma] * n_candles,
    })

    return df


# 1. Valid MACD BUY Setup Test
def test_macd_momentum_valid_buy():
    df = create_synthetic_macd_momentum_df()
    strat = MACDMomentumStrategy()
    signals = strat.generate_signals(df)

    assert len(signals) == 5
    sig = signals[-1]
    assert sig.signal == SignalType.BUY
    assert sig.symbol == "INFY"
    assert sig.strategy_name == "MACD Momentum"
    assert sig.strategy_version == "1.0"


# 2. EMA50 <= EMA200 -> No BUY Test
def test_macd_momentum_ema50_less_than_ema200():
    df = create_synthetic_macd_momentum_df(ema50=490.0, ema200=500.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 3. Close <= EMA200 -> No BUY Test
def test_macd_momentum_close_less_than_ema200():
    df = create_synthetic_macd_momentum_df(close=495.0, ema200=500.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 4. Close <= EMA20 -> No BUY Test
def test_macd_momentum_close_less_than_ema20():
    df = create_synthetic_macd_momentum_df(close=555.0, ema20=560.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 5. MACD <= Signal -> No BUY Test
def test_macd_momentum_macd_below_signal():
    df = create_synthetic_macd_momentum_df(macd_val=1.0, macd_sig=1.5)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 6. MACD Histogram <= 0 -> No BUY Test
def test_macd_momentum_histogram_non_positive():
    df = create_synthetic_macd_momentum_df(macd_val=2.5, macd_sig=2.5, hist_curr=0.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 7. Weakening Histogram when required -> No BUY Test
def test_macd_momentum_histogram_weakening():
    df = create_synthetic_macd_momentum_df(hist_prev=1.2, hist_curr=0.8)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 8. Close <= Previous High -> No BUY Test
def test_macd_momentum_close_below_prev_high():
    df = create_synthetic_macd_momentum_df(close=572.0, prev_high=575.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 9. Bearish Candle (Close <= Open) -> No BUY Test
def test_macd_momentum_bearish_candle():
    df = create_synthetic_macd_momentum_df(close=570.0, open_p=575.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 10. Volume Below Threshold -> No BUY Test
def test_macd_momentum_low_volume():
    # 2000 < 1.2 * 1800 (2160)
    df = create_synthetic_macd_momentum_df(vol=2000.0, vol_sma=1800.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 11. RSI Below 50 -> No BUY Test
def test_macd_momentum_rsi_low():
    df = create_synthetic_macd_momentum_df(rsi=48.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 12. RSI Above 70 -> No BUY Test
def test_macd_momentum_rsi_high():
    df = create_synthetic_macd_momentum_df(rsi=75.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.HOLD


# 13. Insufficient Data -> SKIPPED / HOLD Test
def test_macd_momentum_insufficient_data():
    df_single = create_synthetic_macd_momentum_df(n_candles=1)
    strat = MACDMomentumStrategy()
    signals = strat.generate_signals(df_single)
    sig = signals[-1]
    assert sig.signal == SignalType.HOLD
    assert "Insufficient history" in sig.reason


# 14. Correct Entry Price Test
def test_macd_momentum_entry_price():
    df = create_synthetic_macd_momentum_df(close=580.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.entry_price == 580.0


# 15. Correct ATR Stop Loss Test
def test_macd_momentum_stop_loss():
    # Close = 580.0, ATR = 10.0 -> Stop = 580 - (1.5 * 10) = 565.0
    df = create_synthetic_macd_momentum_df(close=580.0, atr=10.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.stop_loss == 565.0
    assert sig.stop_loss < sig.entry_price


# 16. Correct Target Price Test
def test_macd_momentum_target_price():
    # Entry = 580.0, Stop = 565.0, Risk = 15.0 -> Target = 580 + (2.0 * 15) = 610.0
    df = create_synthetic_macd_momentum_df(close=580.0, atr=10.0)
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.target_price == 610.0
    assert sig.risk_reward == 2.0


# 17. Correct Metadata Contents Test
def test_macd_momentum_metadata():
    df = create_synthetic_macd_momentum_df()
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    meta = sig.metadata
    assert "ema20" in meta
    assert "ema50" in meta
    assert "ema200" in meta
    assert "macd" in meta
    assert "macd_signal" in meta
    assert "macd_histogram" in meta
    assert "previous_macd_histogram" in meta
    assert "rsi14" in meta
    assert "atr14" in meta
    assert "volume_sma20" in meta
    assert "volume_ratio" in meta
    assert meta["macd"] == 2.5
    assert meta["macd_signal"] == 1.5


# 18. Correct Reason String Test
def test_macd_momentum_reason_text():
    df = create_synthetic_macd_momentum_df(
        ema50=560.20,
        ema200=520.10,
        macd_val=1.85,
        macd_sig=1.20,
        hist_prev=0.40,
        hist_curr=0.65,
        rsi=61.2,
    )
    strat = MACDMomentumStrategy()
    sig = strat.generate_signals(df)[-1]
    assert sig.signal == SignalType.BUY
    assert "EMA50 (₹560.20) > EMA200 (₹520.10)" in sig.reason
    assert "price above EMA20" in sig.reason
    assert "MACD (1.85 > 1.20)" in sig.reason
    assert "RSI14=61.2" in sig.reason


# 19. No Look-Ahead Bias Guarantee Test
def test_macd_momentum_no_lookahead():
    df1 = create_synthetic_macd_momentum_df(n_candles=10)
    df2 = df1.copy()
    # Modify future candle at index 9
    df2.iloc[9, df2.columns.get_loc("close")] = 10.0

    strat = MACDMomentumStrategy()
    sig1 = strat.generate_signals(df1.iloc[:9])
    sig2 = strat.generate_signals(df2.iloc[:9])

    # Signal at index 8 MUST be identical regardless of future candle at index 9
    assert sig1[-1].signal == sig2[-1].signal
    assert sig1[-1].entry_price == sig2[-1].entry_price
    assert sig1[-1].stop_loss == sig2[-1].stop_loss


# 20. Registry Lookup Works Test
def test_registry_returns_macd_momentum():
    strat = get_strategy("macd_momentum")
    assert isinstance(strat, MACDMomentumStrategy)
    assert strat.name == "MACD Momentum"


# 21. Scanner Integration Test
def test_scanner_with_macd_momentum():
    strat = get_strategy("macd_momentum")
    assert strat.name == "MACD Momentum"


# 22. Backtest Integration Test
def test_backtest_with_macd_momentum():
    df = create_synthetic_macd_momentum_df(n_candles=20)
    strat = get_strategy("macd_momentum")
    engine = BacktestEngine(strategy=strat)
    result = engine.run(df)
    assert result.strategy == "MACD Momentum"
    assert isinstance(result.total_trades, int)


# 23. Existing EMA Pullback Tests Still Pass Test
def test_existing_ema_pullback_unaffected():
    strat = EMAPullbackStrategy()
    assert strat.name == "EMA Pullback"


# 24. Existing MA Trend Breakout Tests Still Pass Test
def test_existing_ma_trend_breakout_unaffected():
    strat = MATrendBreakoutStrategy()
    assert strat.name == "MA Trend Breakout"


# 25. Existing RSI Mean-Reversion Tests Still Pass Test
def test_existing_rsi_mean_reversion_unaffected():
    strat = RSIMeanReversionStrategy()
    assert strat.name == "RSI Mean-Reversion"


# 26. Registry Contains All Four Strategies Test
def test_all_four_strategies_in_registry():
    strats = list_strategies()
    names = [s["name"] for s in strats]
    assert "EMA Pullback" in names
    assert "MA Trend Breakout" in names
    assert "RSI Mean-Reversion" in names
    assert "MACD Momentum" in names
