import numpy as np
import pandas as pd


def calculate_tr(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """
    Calculates the True Range (TR) for each candle.

    TR = max(high - low, abs(high - previous_close), abs(low - previous_close))
    """
    prev_close = close.shift(1)
    tr_components = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    )
    return tr_components.max(axis=1)


def calculate_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """
    Calculates Average True Range (ATR) using Wilder-style smoothing.

    Parameters:
    - high: High price series
    - low: Low price series
    - close: Close price series
    - period: Calculation window period (default 14)

    Returns:
    - pandas Series containing ATR values, with initial `period` NaN values.
    """
    if period <= 0:
        raise ValueError("ATR period must be a positive integer > 0")

    if len(high) <= period:
        return pd.Series(np.nan, index=high.index, dtype=float)

    tr = calculate_tr(high, low, close)

    # Wilder's smoothing alpha = 1 / period
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    # Warm-up rule: first period rows are NaN
    atr = atr.copy()
    atr.iloc[:period] = np.nan
    return atr
