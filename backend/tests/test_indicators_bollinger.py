import numpy as np
import pandas as pd
import pytest

from backend.indicators.bollinger import calculate_bollinger_bands
from backend.indicators.engine import calculate_indicators


def test_calculate_bollinger_bands_basic():
    prices = pd.Series([10.0] * 20)
    mb, ub, lb, bw = calculate_bollinger_bands(prices, period=20, num_std=2.0)

    assert len(mb) == 20
    assert pd.isna(mb.iloc[18])
    assert mb.iloc[19] == 10.0
    assert ub.iloc[19] == 10.0
    assert lb.iloc[19] == 10.0
    assert bw.iloc[19] == 0.0


def test_calculate_bollinger_bands_variance():
    prices = pd.Series([10.0 + i for i in range(20)])
    mb, ub, lb, bw = calculate_bollinger_bands(prices, period=20, num_std=2.0)

    std_val = prices.std()
    assert round(mb.iloc[19], 2) == round(prices.mean(), 2)
    assert round(ub.iloc[19], 2) == round(prices.mean() + 2 * std_val, 2)
    assert round(lb.iloc[19], 2) == round(prices.mean() - 2 * std_val, 2)
    assert bw.iloc[19] > 0


def test_calculate_bollinger_bands_short_series():
    prices = pd.Series([10.0, 12.0, 11.0])
    mb, ub, lb, bw = calculate_bollinger_bands(prices, period=20, num_std=2.0)

    assert all(mb.isna())
    assert all(ub.isna())
    assert all(lb.isna())
    assert all(bw.isna())


def test_calculate_indicators_bollinger_integration():
    df = pd.DataFrame(
        {
            "close": [100.0 + i for i in range(30)],
            "high": [102.0 + i for i in range(30)],
            "low": [98.0 + i for i in range(30)],
            "volume": [1000] * 30,
        }
    )

    res = calculate_indicators(
        df, ["bb_middle_20", "bb_upper_20", "bb_lower_20", "bb_width_20"]
    )

    assert "bb_middle_20" in res.columns
    assert "bb_upper_20" in res.columns
    assert "bb_lower_20" in res.columns
    assert "bb_width_20" in res.columns
    assert pd.notna(res["bb_width_20"].iloc[25])
