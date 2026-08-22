import re
import sqlite3
from typing import List, Optional, Union
import pandas as pd

from backend.database.connection import get_db_connection, DEFAULT_DB_PATH
from .atr import calculate_atr, calculate_tr
from .ema import calculate_ema, calculate_sma
from .macd import calculate_macd
from .price_action import (

    distance_from_ema_pct,
    highest_high,
    lowest_low,
    percentage_change,
)
from .rsi import calculate_rsi
from .volume import calculate_relative_volume, calculate_volume_sma


def get_price_history(
    conn: sqlite3.Connection,
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Retrieves historical daily OHLCV prices for a stock from SQLite.
    Returns a pandas DataFrame sorted chronologically by trade_date ASC.
    """
    query = """
        SELECT p.trade_date, p.open, p.high, p.low, p.close, p.adjusted_close, p.volume
        FROM daily_prices p
        JOIN stocks s ON p.stock_id = s.id
        WHERE s.symbol = ?
    """
    params = [symbol]

    if start_date:
        query += " AND p.trade_date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND p.trade_date <= ?"
        params.append(end_date)

    query += " ORDER BY p.trade_date ASC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    df = pd.read_sql_query(query, conn, params=params)
    return df


def calculate_indicators(df: pd.DataFrame, indicators: List[str]) -> pd.DataFrame:
    """
    High-level interface to compute technical indicators in-memory on a price DataFrame.

    Supported Indicator Format Examples:
    - "ema_9", "ema_20", "ema_50", "ema_100", "ema_200"
    - "sma_20", "sma_50", "sma_200"
    - "rsi_14"
    - "tr", "atr_14"
    - "volume_sma_20"
    - "relative_volume_20", "rvol_20"
    - "dist_ema_20_pct"
    - "pct_change_1"
    - "highest_high_20", "lowest_low_20"

    Returns:
    - New pandas DataFrame with requested indicator columns attached.
    """
    if df.empty:
        return df.copy()

    res_df = df.copy()
    close = res_df["close"] if "close" in res_df.columns else None
    high = res_df["high"] if "high" in res_df.columns else None
    low = res_df["low"] if "low" in res_df.columns else None
    volume = res_df["volume"] if "volume" in res_df.columns else None

    for ind in indicators:
        ind_clean = ind.lower().strip()

        # 1. EMA: ema_<period>
        match_ema = re.match(r"^ema_(\d+)$", ind_clean)
        if match_ema and close is not None:
            period = int(match_ema.group(1))
            res_df[ind] = calculate_ema(close, period)
            continue

        # 2. SMA: sma_<period>
        match_sma = re.match(r"^sma_(\d+)$", ind_clean)
        if match_sma and close is not None:
            period = int(match_sma.group(1))
            res_df[ind] = calculate_sma(close, period)
            continue

        # 3. RSI: rsi_<period>
        match_rsi = re.match(r"^rsi_(\d+)$", ind_clean)
        if match_rsi and close is not None:
            period = int(match_rsi.group(1))
            res_df[ind] = calculate_rsi(close, period)
            continue

        # 4. TR: tr
        if ind_clean == "tr" and high is not None and low is not None and close is not None:
            res_df[ind] = calculate_tr(high, low, close)
            continue

        # 5. ATR: atr_<period>
        match_atr = re.match(r"^atr_(\d+)$", ind_clean)
        if match_atr and high is not None and low is not None and close is not None:
            period = int(match_atr.group(1))
            res_df[ind] = calculate_atr(high, low, close, period)
            continue

        # 6. Volume SMA: volume_sma_<period>
        match_vol_sma = re.match(r"^volume_sma_(\d+)$", ind_clean)
        if match_vol_sma and volume is not None:
            period = int(match_vol_sma.group(1))
            res_df[ind] = calculate_volume_sma(volume, period)
            continue

        # 7. Relative Volume: relative_volume_<period> or rvol_<period>
        match_rvol = re.match(r"^(?:relative_volume|rvol)_(\d+)$", ind_clean)
        if match_rvol and volume is not None:
            period = int(match_rvol.group(1))
            res_df[ind] = calculate_relative_volume(volume, period)
            continue

        # 8. Distance from EMA: dist_ema_<period>_pct
        match_dist_ema = re.match(r"^dist_ema_(\d+)_pct$", ind_clean)
        if match_dist_ema and close is not None:
            period = int(match_dist_ema.group(1))
            ema = calculate_ema(close, period)
            res_df[ind] = distance_from_ema_pct(close, ema)
            continue

        # 9. Pct Change: pct_change_<periods>
        match_pct = re.match(r"^pct_change_(\d+)$", ind_clean)
        if match_pct and close is not None:
            periods = int(match_pct.group(1))
            res_df[ind] = percentage_change(close, periods)
            continue

        # 10. Highest High: highest_high_<period>
        match_hh = re.match(r"^highest_high_(\d+)$", ind_clean)
        if match_hh and high is not None:
            period = int(match_hh.group(1))
            res_df[ind] = highest_high(high, period)
            continue

        # 11. Lowest Low: lowest_low_<period>
        match_ll = re.match(r"^lowest_low_(\d+)$", ind_clean)
        if match_ll and low is not None:
            period = int(match_ll.group(1))
            res_df[ind] = lowest_low(low, period)
            continue

        # 12. MACD: macd, macd_signal, macd_histogram / macd_hist
        if ind_clean in ["macd", "macd_signal", "macd_histogram", "macd_hist"] and close is not None:
            if "macd" not in res_df.columns or "macd_signal" not in res_df.columns or "macd_histogram" not in res_df.columns:
                m_line, s_line, h_line = calculate_macd(close, 12, 26, 9)
                res_df["macd"] = m_line
                res_df["macd_signal"] = s_line
                res_df["macd_histogram"] = h_line
                res_df["macd_hist"] = h_line
            continue


    return res_df
