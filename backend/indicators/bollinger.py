from typing import Tuple
import numpy as np
import pandas as pd
from .ema import calculate_sma


def calculate_bollinger_bands(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Calculates standard Bollinger Bands and Bollinger Band Width.

    Parameters:
    - series: Input price pandas Series (e.g. close price)
    - period: Integer window period for SMA and rolling standard deviation (default: 20)
    - num_std: Multiplier for standard deviation (default: 2.0)

    Returns:
    - Tuple of pandas Series: (middle_band, upper_band, lower_band, band_width)
    """
    if period <= 0:
        raise ValueError("Bollinger Bands period must be > 0")
    if num_std <= 0:
        raise ValueError("Bollinger Bands num_std must be > 0")

    if len(series) < period:
        nan_series = pd.Series(np.nan, index=series.index, dtype=float)
        return nan_series, nan_series, nan_series, nan_series

    middle_band = calculate_sma(series, period)
    rolling_std = series.rolling(window=period, min_periods=period).std()

    upper_band = middle_band + (num_std * rolling_std)
    lower_band = middle_band - (num_std * rolling_std)

    # Band Width = (Upper - Lower) / Middle
    # Handle division by zero / negative / NaN middle band safely
    denom = middle_band.where(middle_band > 0, np.nan)
    band_width = (upper_band - lower_band) / denom

    return middle_band, upper_band, lower_band, band_width
