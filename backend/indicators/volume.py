import pandas as pd
from .ema import calculate_sma


def calculate_volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculates Simple Moving Average (SMA) of Volume over a configurable period.
    """
    return calculate_sma(volume, period)


def calculate_relative_volume(volume: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculates Relative Volume (RVOL) = current_volume / average_volume.

    Parameters:
    - volume: Volume series
    - period: Period for moving average volume (default 20)

    Returns:
    - pandas Series representing relative volume factor (e.g. 1.5 = 50% above average).
    """
    vol_sma = calculate_volume_sma(volume, period)
    return volume / vol_sma
