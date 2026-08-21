from datetime import datetime, timedelta
import logging
from pathlib import Path
import sqlite3
import sys
from typing import List, Tuple

from backend.database.connection import get_db_connection, DEFAULT_DB_PATH
from backend.market_data.downloader import download_stock_history
from backend.scripts.initialize_data import save_stock_prices

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("update_market_data")


def get_active_stocks_with_max_date(conn: sqlite3.Connection) -> List[Tuple[int, str, str, str]]:
    """
    Retrieves all active stocks and their latest stored trade_date.
    Returns a list of tuples: (stock_id, symbol, ticker, max_trade_date or None)
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.symbol, s.ticker, MAX(p.trade_date) as max_date
        FROM stocks s
        LEFT JOIN daily_prices p ON s.id = p.stock_id
        WHERE s.is_active = 1
        GROUP BY s.id, s.symbol, s.ticker;
    """)
    return [(row["id"], row["symbol"], row["ticker"], row["max_date"]) for row in cursor.fetchall()]


def run_market_data_update(db_path: Path = DEFAULT_DB_PATH) -> None:
    print("SwingLens Market Data Daily Update")
    print("==================================\n")

    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}.")
        print("Please run 'python -m backend.scripts.initialize_data' first.")
        sys.exit(1)

    conn = get_db_connection(db_path)
    stocks = get_active_stocks_with_max_date(conn)

    if not stocks:
        print("No active stocks found in database.")
        conn.close()
        return

    print(f"Checking updates for {len(stocks)} active stocks...\n")

    updated_stocks: List[str] = []
    up_to_date_stocks: List[str] = []
    failed_stocks: List[str] = []

    total_new_rows = 0
    total_updated_rows = 0

    today_str = datetime.now().strftime("%Y-%m-%d")

    for idx, (stock_id, symbol, ticker, max_date) in enumerate(stocks, 1):
        sys.stdout.write(f"[{idx}/{len(stocks)}] Checking {symbol} ({ticker})... ")
        sys.stdout.flush()

        try:
            if max_date:
                # Start from the day after the last stored date
                start_dt = datetime.strptime(max_date, "%Y-%m-%d") + timedelta(days=1)
                start_date_str = start_dt.strftime("%Y-%m-%d")
            else:
                # Default to full 5y if no data exists
                start_date_str = None

            if start_date_str and start_date_str > today_str:
                print("UP-TO-DATE (Already latest)")
                up_to_date_stocks.append(symbol)
                continue

            df, errors = download_stock_history(
                ticker,
                start_date=start_date_str,
                end_date=today_str,
            )

            if df is not None and not df.empty:
                inserted, updated = save_stock_prices(conn, stock_id, df)
                conn.commit()

                total_new_rows += inserted
                total_updated_rows += updated

                if inserted > 0 or updated > 0:
                    updated_stocks.append(f"{symbol} (+{inserted} new, {updated} updated)")
                    print(f"UPDATED (+{inserted} rows)")
                else:
                    up_to_date_stocks.append(symbol)
                    print("UP-TO-DATE")
            else:
                if errors and "No historical data" in errors[0]:
                    up_to_date_stocks.append(symbol)
                    print("UP-TO-DATE (No new market rows)")
                else:
                    err_msg = ", ".join(errors) if errors else "No data"
                    failed_stocks.append(f"{symbol}: {err_msg}")
                    print(f"FAILED ({err_msg})")

        except Exception as e:
            conn.rollback()
            failed_stocks.append(f"{symbol}: {e}")
            print(f"FAILED ({e})")

    conn.close()

    print("\n---------------------------------------------")
    print("Daily Update Summary:")
    print(f"Stocks updated     : {len(updated_stocks)}")
    print(f"Stocks up-to-date  : {len(up_to_date_stocks)}")
    print(f"Stocks failed      : {len(failed_stocks)}")
    print(f"\nNew rows inserted  : {total_new_rows:,}")
    print(f"Rows updated       : {total_updated_rows:,}")

    if updated_stocks:
        print("\nUpdated Stocks Detail:")
        for item in updated_stocks:
            print(f"  - {item}")

    if failed_stocks:
        print("\nFailed Stocks Detail:")
        for item in failed_stocks:
            print(f"  - {item}")

    print("\nStatus: COMPLETE")
    print("=============================================")


if __name__ == "__main__":
    run_market_data_update()
