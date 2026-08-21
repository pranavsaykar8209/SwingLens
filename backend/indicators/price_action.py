import pandas as pd


def percentage_change(series: pd.Series, periods: int = 1) -> pd.Series:
    """Calculates percentage change over N periods."""
    return series.pct_change(periods=periods) * 100.0


def daily_return(close: pd.Series) -> pd.Series:
    """Calculates daily fractional return (e.g. 0.02 = +2%)."""
    return close.pct_change(periods=1)


def distance_from_ema_pct(close: pd.Series, ema: pd.Series) -> pd.Series:
    """Calculates percentage distance of close price from EMA."""
    return ((close - ema) / ema) * 100.0


def highest_high(high: pd.Series, period: int) -> pd.Series:
    """Calculates rolling highest high over N periods."""
    return high.rolling(window=period, min_periods=period).max()


def lowest_low(low: pd.Series, period: int) -> pd.Series:
    """Calculates rolling lowest low over N periods."""
    return low.rolling(window=period, min_periods=period).min()


def rolling_highest_close(close: pd.Series, period: int) -> pd.Series:
    """Calculates rolling highest close price over N periods."""
    return close.rolling(window=period, min_periods=period).max()


def rolling_lowest_close(close: pd.Series, period: int) -> pd.Series:
    """Calculates rolling lowest close price over N periods."""
    return close.rolling(window=period, min_periods=period).min()


def series_greater_than(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """Returns boolean series indicating if series_a > series_b."""
    return series_a > series_b


def ema_relationship(ema_fast: pd.Series, ema_slow: pd.Series) -> pd.Series:
    """Returns boolean series indicating if fast EMA > slow EMA (bullish alignment)."""
    return ema_fast > ema_slow


def price_above_ema(close: pd.Series, ema: pd.Series) -> pd.Series:
    """Returns boolean series indicating if close > EMA."""
    return close > ema


def crossed_above(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """
    Returns boolean series indicating exact candle where series_a crosses above series_b.
    True ONLY on the candle of crossing (prev_a <= prev_b AND curr_a > curr_b).
    """
    prev_a = series_a.shift(1)
    prev_b = series_b.shift(1)
    return (prev_a <= prev_b) & (series_a > series_b)


def crossed_below(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """
    Returns boolean series indicating exact candle where series_a crosses below series_b.
    True ONLY on the candle of crossing (prev_a >= prev_b AND curr_a < curr_b).
    """
    prev_a = series_a.shift(1)
    prev_b = series_b.shift(1)
    return (prev_a >= prev_b) & (series_a < series_b)
