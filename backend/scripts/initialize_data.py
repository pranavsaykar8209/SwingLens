from datetime import datetime
import logging
from pathlib import Path
import sqlite3
import sys
from typing import Dict, Any, List

from backend.database.connection import get_db_connection, init_db, DEFAULT_DB_PATH
from backend.market_data.downloader import download_stock_history
from backend.market_data.universe import fetch_nifty_next_50_constituents

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("initialize_data")


def upsert_stock(conn: sqlite3.Connection, stock: Dict[str, Any]) -> int:
    """
    Inserts or updates a stock record in the `stocks` table.
    Returns the stock's integer ID.
    """
    now = datetime.now().isoformat()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO stocks (symbol, ticker, company_name, exchange, series, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            company_name = excluded.company_name,
            exchange = excluded.exchange,
            series = excluded.series,
            is_active = 1,
            updated_at = excluded.updated_at
        RETURNING id;
        """,
        (
            stock["symbol"],
            stock["ticker"],
            stock.get("company_name", stock["symbol"]),
            stock.get("exchange", "NSE"),
            stock.get("series", "EQ"),
            now,
            now,
        ),
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    # Fallback if RETURNING is not supported in an older SQLite version
    cursor.execute("SELECT id FROM stocks WHERE symbol = ?", (stock["symbol"],))
    return cursor.fetchone()[0]


def save_stock_prices(conn: sqlite3.Connection, stock_id: int, df) -> tuple[int, int]:
    """
    Saves or updates daily prices for a given stock using SQLite UPSERT.
    Returns (rows_inserted, rows_updated).
    """
    if df is None or df.empty:
        return 0, 0

    now = datetime.now().isoformat()
    cursor = conn.cursor()

    # Get count of existing rows before UPSERT to calculate inserted vs updated
    trade_dates = list(df["trade_date"])
    placeholders = ",".join(["?"] * len(trade_dates))
    cursor.execute(
        f"SELECT COUNT(*) FROM daily_prices WHERE stock_id = ? AND trade_date IN ({placeholders})",
        [stock_id] + trade_dates,
    )
    existing_count = cursor.fetchone()[0]

    insert_sql = """
        INSERT INTO daily_prices (stock_id, trade_date, open, high, low, close, adjusted_close, volume, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stock_id, trade_date) DO UPDATE SET
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            adjusted_close = excluded.adjusted_close,
            volume = excluded.volume;
    """

    records = []
    for _, row in df.iterrows():
        records.append((
            stock_id,
            row["trade_date"],
            float(row["open"]),
            float(row["high"]),
            float(row["low"]),
            float(row["close"]),
            float(row.get("adjusted_close", row["close"])),
            int(row["volume"]) if not pd_isna(row["volume"]) else 0,
            now,
        ))

    cursor.executemany(insert_sql, records)

    total_records = len(records)
    rows_updated = existing_count
    rows_inserted = total_records - rows_updated

    return rows_inserted, rows_updated


def pd_isna(val) -> bool:
    try:
        import math
        return val is None or math.isnan(val)
    except Exception:
        return False


def run_initialization(db_path: Path = DEFAULT_DB_PATH, period: str = "5y") -> None:
    print("SwingLens Data Initialization")
    print("=============================\n")

    # 1. Initialize Database Schema
    init_db(db_path)
    conn = get_db_connection(db_path)

    # 2. Fetch Constituents
    universe_name = "NIFTY NEXT 50"
    constituents = fetch_nifty_next_50_constituents()
    total_stocks = len(constituents)

    print(f"Universe: {universe_name}")
    print(f"Stocks found: {total_stocks}\n")
    print("Downloading historical data...")

    successful_count = 0
    failed_count = 0
    total_inserted = 0
    total_updated = 0

    earliest_date_found = None
    latest_date_found = None

    failed_details: List[str] = []

    # 3. Process stocks sequentially with progress indicators
    for idx, stock in enumerate(constituents, 1):
        symbol = stock["symbol"]
        ticker = stock["ticker"]
        sys.stdout.write(f"[{idx}/{total_stocks}] Downloading {symbol} ({ticker})... ")
        sys.stdout.flush()

        try:
            # Insert / Update stock record
            stock_id = upsert_stock(conn, stock)

            # Download history
            df, errors = download_stock_history(ticker, period=period)

            if df is not None and not df.empty:
                inserted, updated = save_stock_prices(conn, stock_id, df)
                conn.commit()

                total_inserted += inserted
                total_updated += updated
                successful_count += 1

                stock_min_date = df["trade_date"].min()
                stock_max_date = df["trade_date"].max()

                if earliest_date_found is None or stock_min_date < earliest_date_found:
                    earliest_date_found = stock_min_date
                if latest_date_found is None or stock_max_date > latest_date_found:
                    latest_date_found = stock_max_date

                print(f"OK ({len(df)} rows)")
            else:
                failed_count += 1
                err_msg = ", ".join(errors) if errors else "Empty dataset"
                failed_details.append(f"{symbol}: {err_msg}")
                print(f"FAILED ({err_msg})")

        except Exception as e:
            conn.rollback()
            failed_count += 1
            failed_details.append(f"{symbol}: {e}")
            print(f"FAILED ({e})")

    conn.close()

    # Print Summary Output
    print("\n---------------------------------------------")
    print(f"Successful: {successful_count}")
    print(f"Failed: {failed_count}")
    if failed_details:
        print("Failure log:")
        for err in failed_details:
            print(f"  - {err}")

    print(f"\nRows inserted: {total_inserted:,}")
    print(f"Rows updated: {total_updated:,}")
    print(f"\nEarliest date: {earliest_date_found or 'N/A'}")
    print(f"Latest date: {latest_date_found or 'N/A'}")
    print(f"\nDatabase:\n{db_path}")
    print("\nStatus: COMPLETE")
    print("=============================================")


if __name__ == "__main__":
    run_initialization()
