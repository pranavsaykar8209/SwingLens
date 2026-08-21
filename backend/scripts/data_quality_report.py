from collections import Counter
from datetime import datetime
from pathlib import Path
import sqlite3
import sys
from typing import Dict, Any, List, Tuple

from backend.database.connection import get_db_connection, DEFAULT_DB_PATH


def check_database_integrity(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Validates database connectivity, required table presence, and foreign key integrity.
    """
    cursor = conn.cursor()

    # Table existence
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    missing_tables = [t for t in ["stocks", "daily_prices"] if t not in tables]

    # Foreign key check
    cursor.execute("PRAGMA foreign_key_check;")
    fk_errors = cursor.fetchall()

    is_valid = len(missing_tables) == 0 and len(fk_errors) == 0
    return {
        "is_valid": is_valid,
        "missing_tables": missing_tables,
        "fk_errors_count": len(fk_errors),
        "tables": tables,
    }


def check_stock_universe(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Audits the stocks table for total count, duplicate symbols/tickers,
    missing symbol fields, and active status breakdown.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, ticker, is_active FROM stocks;")
    rows = cursor.fetchall()

    total_stocks = len(rows)
    symbols = [r["symbol"] for r in rows if r["symbol"]]
    tickers = [r["ticker"] for r in rows if r["ticker"]]

    missing_symbols = sum(1 for r in rows if not r["symbol"])
    missing_tickers = sum(1 for r in rows if not r["ticker"])

    symbol_counts = Counter(symbols)
    ticker_counts = Counter(tickers)

    dup_symbols = [s for s, c in symbol_counts.items() if c > 1]
    dup_tickers = [t for t, c in ticker_counts.items() if c > 1]

    active_stocks = sum(1 for r in rows if r["is_active"] == 1)
    inactive_stocks = total_stocks - active_stocks

    return {
        "total_stocks": total_stocks,
        "active_stocks": active_stocks,
        "inactive_stocks": inactive_stocks,
        "dup_symbols_count": len(dup_symbols),
        "dup_tickers_count": len(dup_tickers),
        "missing_symbols": missing_symbols,
        "missing_tickers": missing_tickers,
    }


def check_duplicate_candles(conn: sqlite3.Connection) -> int:
    """
    Checks for duplicate (stock_id, trade_date) pairs in daily_prices.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT stock_id, trade_date, COUNT(*) as cnt
        FROM daily_prices
        GROUP BY stock_id, trade_date
        HAVING cnt > 1;
    """)
    return len(cursor.fetchall())


def check_missing_values(conn: sqlite3.Connection) -> Dict[str, int]:
    """
    Checks for missing (NULL) values in daily_prices columns.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            SUM(CASE WHEN open IS NULL THEN 1 ELSE 0 END) as missing_open,
            SUM(CASE WHEN high IS NULL THEN 1 ELSE 0 END) as missing_high,
            SUM(CASE WHEN low IS NULL THEN 1 ELSE 0 END) as missing_low,
            SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) as missing_close,
            SUM(CASE WHEN adjusted_close IS NULL THEN 1 ELSE 0 END) as missing_adj_close,
            SUM(CASE WHEN volume IS NULL THEN 1 ELSE 0 END) as missing_volume
        FROM daily_prices;
    """)
    row = cursor.fetchone()
    return {
        "missing_open": row["missing_open"] or 0,
        "missing_high": row["missing_high"] or 0,
        "missing_low": row["missing_low"] or 0,
        "missing_close": row["missing_close"] or 0,
        "missing_adj_close": row["missing_adj_close"] or 0,
        "missing_volume": row["missing_volume"] or 0,
        "total_missing_ohlc": (row["missing_open"] or 0)
        + (row["missing_high"] or 0)
        + (row["missing_low"] or 0)
        + (row["missing_close"] or 0),
    }


def check_ohlc_errors(conn: sqlite3.Connection) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Flags invalid OHLC relationship rows:
    - high < low
    - open > high or open < low
    - close > high or close < low
    - open <= 0 or high <= 0 or low <= 0 or close <= 0
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT stock_id, trade_date, open, high, low, close
        FROM daily_prices
        WHERE high < low
           OR open > high
           OR open < low
           OR close > high
           OR close < low
           OR open <= 0
           OR high <= 0
           OR low <= 0
           OR close <= 0;
    """)
    invalid_rows = [dict(r) for r in cursor.fetchall()]
    return len(invalid_rows), invalid_rows


def check_volume_validation(conn: sqlite3.Connection) -> Dict[str, int]:
    """
    Audits volume values for negative, zero, or missing numbers.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            SUM(CASE WHEN volume < 0 THEN 1 ELSE 0 END) as negative_volume,
            SUM(CASE WHEN volume = 0 THEN 1 ELSE 0 END) as zero_volume,
            SUM(CASE WHEN volume IS NULL THEN 1 ELSE 0 END) as missing_volume
        FROM daily_prices;
    """)
    row = cursor.fetchone()
    return {
        "negative_volume": row["negative_volume"] or 0,
        "zero_volume": row["zero_volume"] or 0,
        "missing_volume": row["missing_volume"] or 0,
    }


def check_date_consistency(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Audits overall trade date ranges and flags stocks lagging behind the universe.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.symbol, MIN(p.trade_date) as min_date, MAX(p.trade_date) as max_date, COUNT(p.trade_date) as row_count
        FROM stocks s
        JOIN daily_prices p ON s.id = p.stock_id
        GROUP BY s.symbol;
    """)
    stock_date_summaries = cursor.fetchall()

    if not stock_date_summaries:
        return {
            "overall_min_date": None,
            "overall_max_date": None,
            "most_common_latest_date": None,
            "stocks_with_different_latest_date": [],
            "stocks_with_few_rows": [],
        }

    overall_min_date = min(r["min_date"] for r in stock_date_summaries if r["min_date"])
    overall_max_date = max(r["max_date"] for r in stock_date_summaries if r["max_date"])

    max_dates = [r["max_date"] for r in stock_date_summaries if r["max_date"]]
    date_counter = Counter(max_dates)
    most_common_latest_date = date_counter.most_common(1)[0][0] if date_counter else None

    different_latest_date = [
        f"{r['symbol']} ({r['max_date']})"
        for r in stock_date_summaries
        if r["max_date"] != most_common_latest_date
    ]

    # Find stocks with significantly fewer rows (e.g. < 500 rows vs typical ~1239 for 5y)
    stocks_with_few_rows = [
        f"{r['symbol']} ({r['row_count']} rows)"
        for r in stock_date_summaries
        if r["row_count"] < 500
    ]

    return {
        "overall_min_date": overall_min_date,
        "overall_max_date": overall_max_date,
        "most_common_latest_date": most_common_latest_date,
        "stocks_with_different_latest_date": different_latest_date,
        "stocks_with_few_rows": stocks_with_few_rows,
    }


def check_suspicious_price_moves(
    conn: sqlite3.Connection, threshold_pct: float = 25.0
) -> List[Dict[str, Any]]:
    """
    Identifies extreme single-day close-to-close price movements (> threshold_pct).
    These are flagged as WARNING (not errors) to account for stock splits, bonuses, or circuit moves.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.symbol, p.trade_date, p.open, p.high, p.low, p.close, p.volume
        FROM daily_prices p
        JOIN stocks s ON p.stock_id = s.id
        ORDER BY s.symbol, p.trade_date;
    """)
    rows = cursor.fetchall()

    warnings = []
    prev_symbol = None
    prev_close = None

    for r in rows:
        sym = r["symbol"]
        close_p = r["close"]
        if sym == prev_symbol and prev_close and prev_close > 0:
            change_pct = abs(close_p - prev_close) / prev_close * 100.0
            if change_pct >= threshold_pct:
                warnings.append({
                    "symbol": sym,
                    "trade_date": r["trade_date"],
                    "prev_close": prev_close,
                    "close": close_p,
                    "change_pct": round(change_pct, 2),
                })
        prev_symbol = sym
        prev_close = close_p

    return warnings


def get_per_stock_audit_table(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Generates a per-stock metric breakdown table:
    Symbol | Rows | First Date | Last Date | Missing | Errors | Status
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            s.id,
            s.symbol,
            COUNT(p.trade_date) as row_count,
            MIN(p.trade_date) as first_date,
            MAX(p.trade_date) as last_date,
            SUM(CASE WHEN p.open IS NULL OR p.high IS NULL OR p.low IS NULL OR p.close IS NULL THEN 1 ELSE 0 END) as missing_ohlc,
            SUM(CASE WHEN p.high < p.low OR p.open > p.high OR p.open < p.low OR p.close > p.high OR p.close < p.low OR p.close <= 0 THEN 1 ELSE 0 END) as ohlc_errors
        FROM stocks s
        LEFT JOIN daily_prices p ON s.id = p.stock_id
        GROUP BY s.id, s.symbol
        ORDER BY s.symbol;
    """)
    results = []
    for r in cursor.fetchall():
        row_cnt = r["row_count"]
        missing = r["missing_ohlc"] or 0
        errs = r["ohlc_errors"] or 0

        status = "OK"
        if errs > 0 or missing > 0:
            status = "ERROR"
        elif row_cnt < 500:
            status = "NEW_LISTING"

        results.append({
            "symbol": r["symbol"],
            "rows": row_cnt,
            "first_date": r["first_date"] or "N/A",
            "last_date": r["last_date"] or "N/A",
            "missing": missing,
            "errors": errs,
            "status": status,
        })
    return results


def run_data_quality_report(db_path: Path = DEFAULT_DB_PATH) -> str:
    """
    Runs the complete data quality inspection on the target database
    and prints a formatted report.
    Returns audit status: PASS | WARNING | ERROR.
    """
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        print(f"Error: Database file does not exist at {db_path_obj}")
        return "ERROR"

    conn = get_db_connection(db_path_obj)

    # 1. Integrity
    integrity_res = check_database_integrity(conn)
    if not integrity_res["is_valid"]:
        print("ERROR: Database schema or foreign key integrity check failed.")
        conn.close()
        return "ERROR"

    # 2. Universe
    universe_res = check_stock_universe(conn)

    # 3. Duplicate Candles
    duplicate_candles = check_duplicate_candles(conn)

    # 4. Missing Values
    missing_res = check_missing_values(conn)

    # 5. OHLC Errors
    ohlc_error_count, _ = check_ohlc_errors(conn)

    # 6. Volume
    volume_res = check_volume_validation(conn)

    # 7. Date Consistency
    date_res = check_date_consistency(conn)

    # 8. Suspicious Moves
    price_warnings = check_suspicious_price_moves(conn)

    # Total rows in daily_prices
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_prices;")
    total_price_rows = cursor.fetchone()[0]

    # Per stock table
    per_stock_table = get_per_stock_audit_table(conn)
    conn.close()

    # Determine Final Status
    final_status = "PASS"
    if ohlc_error_count > 0 or duplicate_candles > 0 or missing_res["total_missing_ohlc"] > 0:
        final_status = "ERROR"
    elif price_warnings or date_res["stocks_with_different_latest_date"]:
        final_status = "WARNING"

    # Print Summary Output
    print("\nSwingLens Data Quality Report")
    print("=============================")
    print(f"\nDatabase:\n{db_path_obj}\n")

    print("STOCKS")
    print("------")
    print(f"Total stocks        : {universe_res['total_stocks']}")
    print(f"Active stocks       : {universe_res['active_stocks']}")
    print(f"Inactive stocks     : {universe_res['inactive_stocks']}")
    print(f"Duplicate symbols   : {universe_res['dup_symbols_count']}")
    print(f"Duplicate tickers   : {universe_res['dup_tickers_count']}")

    print("\nPRICE DATA")
    print("----------")
    print(f"Total rows          : {total_price_rows:,}")
    print(f"Earliest date       : {date_res['overall_min_date']}")
    print(f"Latest date         : {date_res['overall_max_date']}")

    print("\nDUPLICATES")
    print("----------")
    print(f"Duplicate candles   : {duplicate_candles}")

    print("\nMISSING DATA")
    print("------------")
    print(f"Missing OHLC        : {missing_res['total_missing_ohlc']}")
    print(f"Missing adj close   : {missing_res['missing_adj_close']}")
    print(f"Missing volume      : {missing_res['missing_volume']}")

    print("\nOHLC ERRORS")
    print("-----------")
    print(f"Invalid OHLC rows   : {ohlc_error_count}")

    print("\nVOLUME")
    print("------")
    print(f"Negative volume     : {volume_res['negative_volume']}")
    print(f"Zero volume         : {volume_res['zero_volume']}")

    print("\nDATE CONSISTENCY")
    print("----------------")
    print(f"Most common latest date: {date_res['most_common_latest_date']}")
    print(f"Stocks with different latest date: {len(date_res['stocks_with_different_latest_date'])}")
    if date_res["stocks_with_different_latest_date"]:
        for item in date_res["stocks_with_different_latest_date"]:
            print(f"  - {item}")

    print("\nWARNINGS (Suspicious Price Moves >25%)")
    print("--------------------------------------")
    print(f"Total price warnings: {len(price_warnings)}")
    if price_warnings:
        for w in price_warnings[:10]:  # Limit output to top 10
            print(f"  - {w['symbol']} on {w['trade_date']}: {w['prev_close']} -> {w['close']} ({w['change_pct']}%)")
        if len(price_warnings) > 10:
            print(f"  ... and {len(price_warnings) - 10} more.")

    print("\n---------------------------------------------")
    print(f"FINAL STATUS        : {final_status}")
    print("=============================================\n")

    # Print Per-Stock Table
    print("PER-STOCK BREAKDOWN")
    print("-------------------")
    header = f"{'Symbol':<14} | {'Rows':<6} | {'First Date':<10} | {'Last Date':<10} | {'Missing':<7} | {'Errors':<6} | {'Status'}"
    print(header)
    print("-" * len(header))

    for row in per_stock_table:
        print(
            f"{row['symbol']:<14} | {row['rows']:<6} | {row['first_date']:<10} | {row['last_date']:<10} | {row['missing']:<7} | {row['errors']:<6} | {row['status']}"
        )

    return final_status


if __name__ == "__main__":
    run_data_quality_report()
