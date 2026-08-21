import pandas as pd
import pytest
from backend.market_data.validator import validate_ohlcv_row, validate_ohlcv_dataframe


def test_validate_ohlcv_row_valid():
    row = {"open": 100.0, "high": 110.0, "low": 95.0, "close": 105.0, "volume": 5000}
    is_valid, reason = validate_ohlcv_row(row)
    assert is_valid is True
    assert reason == ""


def test_validate_ohlcv_row_invalid_high_low():
    row = {"open": 100.0, "high": 90.0, "low": 95.0, "close": 105.0, "volume": 5000}
    is_valid, reason = validate_ohlcv_row(row)
    assert is_valid is False
    assert "High (90.0) < Low (95.0)" in reason


def test_validate_ohlcv_row_invalid_volume():
    row = {"open": 100.0, "high": 110.0, "low": 95.0, "close": 105.0, "volume": -10}
    is_valid, reason = validate_ohlcv_row(row)
    assert is_valid is False
    assert "Invalid volume" in reason


def test_validate_ohlcv_row_missing_value():
    row = {"open": 100.0, "high": None, "low": 95.0, "close": 105.0, "volume": 5000}
    is_valid, reason = validate_ohlcv_row(row)
    assert is_valid is False
    assert "Invalid or non-positive price" in reason


def test_validate_ohlcv_dataframe():
    df = pd.DataFrame([
        {"trade_date": "2024-01-01", "open": 100.0, "high": 110.0, "low": 95.0, "close": 105.0, "volume": 5000},
        {"trade_date": "2024-01-02", "open": 105.0, "high": 100.0, "low": 95.0, "close": 105.0, "volume": 5000},  # Invalid high < open
        {"trade_date": "2024-01-01", "open": 100.0, "high": 110.0, "low": 95.0, "close": 106.0, "volume": 6000},  # Duplicate trade_date
    ])

    df_valid, errors = validate_ohlcv_dataframe(df)

    # Should remove row 1 (invalid high) and deduplicate row 2
    assert len(df_valid) == 1
    assert len(errors) >= 2
    assert df_valid.iloc[0]["close"] == 106.0  # Keeps last duplicate
