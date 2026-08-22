from typing import Tuple
import numpy as np
import pandas as pd
from .ema import calculate_ema


def calculate_macd(
    close: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculates standard MACD (Moving Average Convergence Divergence).

    Parameters:
    - close: pandas Series containing close prices.
    - fast_period: Fast EMA period (default: 12).
    - slow_period: Slow EMA period (default: 26).
    - signal_period: Signal Line EMA period (default: 9).

    Returns:
    - Tuple[macd_line, signal_line, histogram] as pandas Series.
    """
    if close.empty or len(close) < slow_period:
        nan_s = pd.Series(np.nan, index=close.index, dtype=float)
        return nan_s, nan_s, nan_s

    fast_ema = calculate_ema(close, fast_period)
    slow_ema = calculate_ema(close, slow_period)
    macd_line = fast_ema - slow_ema

    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    warmup_period = slow_period + signal_period - 2
    signal_line = signal_line.copy()
    signal_line.iloc[: min(warmup_period, len(signal_line))] = np.nan

    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
