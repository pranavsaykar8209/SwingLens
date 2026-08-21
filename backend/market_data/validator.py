import logging
from typing import Tuple, List, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)


def validate_ohlcv_row(row: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates a single OHLCV row.
    Returns (is_valid, error_reason).
    """
    open_p = row.get("open")
    high_p = row.get("high")
    low_p = row.get("low")
    close_p = row.get("close")
    volume = row.get("volume")

    # 1. Missing / None values
    for name, val in [("open", open_p), ("high", high_p), ("low", low_p), ("close", close_p)]:
        if val is None or pd.isna(val) or val <= 0:
            return False, f"Invalid or non-positive price for {name}: {val}"

    if volume is None or pd.isna(volume) or volume < 0:
        return False, f"Invalid volume: {volume}"

    # 2. OHLC relationship checks
    if high_p < low_p:
        return False, f"High ({high_p}) < Low ({low_p})"
    if high_p < open_p or high_p < close_p:
        return False, f"High ({high_p}) lower than Open ({open_p}) or Close ({close_p})"
    if low_p > open_p or low_p > close_p:
        return False, f"Low ({low_p}) higher than Open ({open_p}) or Close ({close_p})"

    return True, ""


def validate_ohlcv_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Validates a pandas DataFrame containing OHLCV prices.
    Expects columns or index to include: Date/trade_date, Open, High, Low, Close, Volume.

    Returns:
    - Cleaned, valid DataFrame with normalized column names.
    - List of validation warnings/errors encountered.
    """
    errors: List[str] = []

    if df.empty:
        errors.append("DataFrame is empty.")
        return pd.DataFrame(), errors

    # Standardize column names to lowercase
    df_clean = df.copy()
    col_map = {}
    for col in df_clean.columns:
        c_lower = str(col).lower().replace(" ", "_")
        if c_lower in ["open", "high", "low", "close", "adj_close", "adjusted_close", "volume", "date", "trade_date"]:
            col_map[col] = c_lower
    df_clean = df_clean.rename(columns=col_map)

    required_cols = ["open", "high", "low", "close"]
    for req in required_cols:
        if req not in df_clean.columns:
            errors.append(f"Missing required column: {req}")
            return pd.DataFrame(), errors

    valid_mask = []
    for idx, row in df_clean.iterrows():
        row_dict = {
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "close": row.get("close"),
            "volume": row.get("volume", 0),
        }
        is_valid, reason = validate_ohlcv_row(row_dict)
        if not is_valid:
            errors.append(f"Row {idx}: {reason}")
            valid_mask.append(False)
        else:
            valid_mask.append(True)

    df_valid = df_clean[valid_mask].copy()

    # Deduplicate rows by trade_date
    if "trade_date" in df_valid.columns:
        dup_count = df_valid.duplicated(subset=["trade_date"]).sum()
        if dup_count > 0:
            errors.append(f"Removed {dup_count} duplicate trade_date rows.")
            df_valid = df_valid.drop_duplicates(subset=["trade_date"], keep="last")

    return df_valid, errors
