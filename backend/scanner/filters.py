import sqlite3
from typing import Any, Dict, List, Optional
import pandas as pd


def get_active_universe_constituents(
    conn: sqlite3.Connection,
    index_name: str = "NIFTY_NEXT_50",
    as_of_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Dynamically fetches active stock members for a specified index from SQLite `index_memberships`.
    
    If `as_of_date` is specified (YYYY-MM-DD), respects historical membership:
    `valid_from <= as_of_date AND (valid_to IS NULL OR as_of_date <= valid_to)`.
    If `as_of_date` is None, returns currently active members (`valid_to IS NULL`).
    
    Returns a list of dicts with stock details (`id`, `symbol`, `company_name`, `ticker`, `exchange`, `series`).
    """
    cursor = conn.cursor()
    if as_of_date:
        query = """
            SELECT s.id, s.symbol, s.company_name, s.ticker, s.exchange, s.series
            FROM index_memberships m
            JOIN stocks s ON m.stock_id = s.id
            WHERE m.index_name = ?
              AND m.valid_from <= ?
              AND (m.valid_to IS NULL OR ? <= m.valid_to)
            ORDER BY s.symbol ASC;
        """
        cursor.execute(query, (index_name, as_of_date, as_of_date))
    else:
        query = """
            SELECT s.id, s.symbol, s.company_name, s.ticker, s.exchange, s.series
            FROM index_memberships m
            JOIN stocks s ON m.stock_id = s.id
            WHERE m.index_name = ? AND m.valid_to IS NULL
            ORDER BY s.symbol ASC;
        """
        cursor.execute(query, (index_name,))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def validate_candle_data(
    df: pd.DataFrame,
    min_required_candles: int = 200,
    required_cols: Optional[List[str]] = None,
) -> None:
    """
    Validates that historical daily price DataFrame meets requirements for technical indicator calculation.

    Raises ValueError if data is missing, incomplete, or has fewer candles than `min_required_candles`.
    """
    if df is None or df.empty:
        raise ValueError("No historical daily price data found in database")

    cols = required_cols or ["trade_date", "open", "high", "low", "close", "volume"]
    missing_cols = [c for c in cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required price columns: {missing_cols}")

    if len(df) < min_required_candles:
        raise ValueError(
            f"Insufficient historical data: {len(df)} candles available, minimum {min_required_candles} required"
        )
