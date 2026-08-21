import numpy as np
import pandas as pd


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Exponential Moving Average (EMA) for an arbitrary period.
    Respects warm-up period by setting the first `period - 1` values to NaN.

    Parameters:
    - series: Input pandas Series (e.g. close price)
    - period: Integer smoothing window period (e.g. 9, 20, 50, 100, 200)

    Returns:
    - pandas Series containing EMA values
    """
    if period <= 0:
        raise ValueError("EMA period must be a positive integer > 0")

    if len(series) < period:
        return pd.Series(np.nan, index=series.index, dtype=float)

    # Calculate EMA using standard ewm formula (adjust=False)
    ema = series.ewm(span=period, adjust=False).mean()

    # Apply strict warm-up rule: first period - 1 entries are NaN
    ema = ema.copy()
    ema.iloc[: period - 1] = np.nan
    return ema


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Simple Moving Average (SMA) for an arbitrary period.
    Requires `period` valid observations before producing a value (min_periods=period).

    Parameters:
    - series: Input pandas Series (e.g. close price, volume)
    - period: Integer rolling window period (e.g. 20, 50, 200)

    Returns:
    - pandas Series containing SMA values
    """
    if period <= 0:
        raise ValueError("SMA period must be a positive integer > 0")

    return series.rolling(window=period, min_periods=period).mean()
