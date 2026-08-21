import numpy as np
import pandas as pd
import pytest

from backend.indicators import (
    calculate_ema,
    calculate_sma,
    calculate_rsi,
    calculate_tr,
    calculate_atr,
    calculate_volume_sma,
    calculate_relative_volume,
    percentage_change,
    daily_return,
    distance_from_ema_pct,
    highest_high,
    lowest_low,
    crossed_above,
    crossed_below,
    calculate_indicators,
)


def test_ema_calculation():
    # Simple known dataset: 5 values
    data = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])

    # EMA 3
    ema3 = calculate_ema(data, period=3)

    # First 2 (period - 1 = 2) values must be NaN due to warm-up
    assert np.isnan(ema3.iloc[0])
    assert np.isnan(ema3.iloc[1])
    assert not np.isnan(ema3.iloc[2])

    # Check unrounded float values
    assert isinstance(ema3.iloc[2], float)


def test_ema_insufficient_data():
    data = pd.Series([10.0, 11.0])
    ema5 = calculate_ema(data, period=5)
    assert ema5.isna().all()


def test_sma_calculation():
    data = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    sma3 = calculate_sma(data, period=3)

    # First 2 values NaN
    assert np.isnan(sma3.iloc[0])
    assert np.isnan(sma3.iloc[1])
    # 3rd value = (10 + 20 + 30) / 3 = 20.0
    assert sma3.iloc[2] == 20.0
    # 4th value = (20 + 30 + 40) / 3 = 30.0
    assert sma3.iloc[3] == 30.0


def test_rsi_calculation():
    # Known price series: 15 values
    prices = pd.Series([
        100.0, 102.0, 101.0, 103.0, 105.0,
        104.0, 106.0, 108.0, 107.0, 110.0,
        112.0, 111.0, 113.0, 115.0, 114.0
    ])

    rsi14 = calculate_rsi(prices, period=14)

    # First 14 values must be NaN
    assert rsi14.iloc[:14].isna().all()
    # 15th value (index 14) is calculated
    assert not np.isnan(rsi14.iloc[14])
    assert 0.0 <= rsi14.iloc[14] <= 100.0


def test_atr_calculation():
    high = pd.Series([10.0, 12.0, 11.0, 13.0, 15.0])
    low = pd.Series([8.0, 9.0, 9.5, 10.0, 12.0])
    close = pd.Series([9.0, 11.0, 10.0, 12.0, 14.0])

    tr = calculate_tr(high, low, close)
    assert len(tr) == 5
    assert tr.iloc[0] == 2.0  # 10 - 8

    # ATR 3
    atr3 = calculate_atr(high, low, close, period=3)
    assert atr3.iloc[:3].isna().all()
    assert not np.isnan(atr3.iloc[3])


def test_volume_indicators():
    volume = pd.Series([1000, 2000, 3000, 4000, 5000], dtype=float)

    vol_sma3 = calculate_volume_sma(volume, period=3)
    assert np.isnan(vol_sma3.iloc[1])
    assert vol_sma3.iloc[2] == 2000.0

    rvol3 = calculate_relative_volume(volume, period=3)
    assert np.isnan(rvol3.iloc[1])
    assert rvol3.iloc[2] == 3000.0 / 2000.0  # 1.5


def test_crossovers():
    series_a = pd.Series([10.0, 12.0, 15.0, 13.0, 10.0])
    series_b = pd.Series([11.0, 11.0, 11.0, 11.0, 11.0])

    c_above = crossed_above(series_a, series_b)
    c_below = crossed_below(series_a, series_b)

    # Index 0: a=10, b=11 (no cross) -> False
    # Index 1: a=12, b=11 (prev a=10 <= b=11, curr a=12 > b=11) -> True
    # Index 2: a=15, b=11 (prev a=12 > b=11, curr a=15 > b=11) -> False (already above!)
    # Index 3: a=13, b=11 (already above) -> False
    # Index 4: a=10, b=11 (prev a=13 >= b=11, curr a=10 < b=11) -> crossed_below = True

    assert c_above.iloc[1] == True
    assert c_above.iloc[2] == False

    assert c_below.iloc[3] == False
    assert c_below.iloc[4] == True


def test_price_action_helpers():
    prices = pd.Series([100.0, 110.0, 105.0, 120.0, 115.0])
    pct = percentage_change(prices, periods=1)
    assert pct.iloc[1] == pytest.approx(10.0)  # +10%

    ema = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0])
    dist = distance_from_ema_pct(prices, ema)
    assert dist.iloc[3] == pytest.approx(20.0)  # (120 - 100) / 100 * 100 = 20%

    hh3 = highest_high(prices, period=3)
    assert hh3.iloc[2] == 110.0
    assert hh3.iloc[3] == 120.0


def test_calculate_indicators_engine_api():
    df = pd.DataFrame({
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        "open": [10.0, 11.0, 12.0, 13.0, 14.0],
        "high": [12.0, 13.0, 14.0, 15.0, 16.0],
        "low": [9.0, 10.0, 11.0, 12.0, 13.0],
        "close": [11.0, 12.0, 13.0, 14.0, 15.0],
        "volume": [100, 200, 300, 400, 500],
    })

    indicators_to_calc = [
        "ema_3",
        "sma_3",
        "tr",
        "volume_sma_3",
        "relative_volume_3",
        "pct_change_1",
    ]

    res_df = calculate_indicators(df, indicators_to_calc)

    # Check all requested columns exist
    for col in indicators_to_calc:
        assert col in res_df.columns

    # Verify original df columns remain untouched
    assert list(df.columns) == ["trade_date", "open", "high", "low", "close", "volume"]


def test_no_lookahead_safety():
    """
    Verifies that changing a future candle's price does NOT alter past indicator values.
    """
    prices1 = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0, 20.0])
    prices2 = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0, 999.0])  # Future index 5 modified

    ema1 = calculate_ema(prices1, period=3)
    ema2 = calculate_ema(prices2, period=3)

    # Indices 0..4 must be IDENTICAL between both calculations
    pd.testing.assert_series_equal(ema1.iloc[:5], ema2.iloc[:5])
