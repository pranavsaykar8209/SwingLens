import numpy as np
import pandas as pd


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculates the Relative Strength Index (RSI) using standard Wilder smoothing.

    Parameters:
    - series: Price pandas Series (e.g. close price)
    - period: Calculation period (default 14)

    Returns:
    - pandas Series containing RSI values ranging from 0.0 to 100.0, with initial `period` NaN values.
    """
    if period <= 0:
        raise ValueError("RSI period must be a positive integer > 0")

    if len(series) <= period:
        return pd.Series(np.nan, index=series.index, dtype=float)

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing uses alpha = 1 / period
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # Handle zero loss case (RSI = 100)
    rsi = rsi.where(avg_loss != 0, 100.0)
    # Handle zero gain & zero loss case (RSI = 50)
    rsi = rsi.where((avg_gain != 0) | (avg_loss != 0), 50.0)

    # Warm-up rule: first period rows are NaN
    rsi = rsi.copy()
    rsi.iloc[:period] = np.nan
    return rsi
