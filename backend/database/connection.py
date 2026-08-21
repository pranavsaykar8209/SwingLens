import os
import sqlite3
from pathlib import Path
from typing import Union

DEFAULT_DB_PATH = Path("data/swinglens.db")


def get_db_connection(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Establishes and returns a connection to the SQLite database.
    Ensures foreign keys are enabled.
    """
    db_path_obj = Path(db_path)
    if str(db_path) != ":memory:":
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path_obj))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
    """
    Initializes the database schema including `stocks` and `daily_prices` tables
    and their required indexes.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Table: stocks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            ticker TEXT NOT NULL UNIQUE,
            company_name TEXT,
            exchange TEXT,
            series TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME,
            updated_at DATETIME
        );
    """)

    # Table: daily_prices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            stock_id INTEGER NOT NULL,
            trade_date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adjusted_close REAL,
            volume INTEGER,
            created_at DATETIME,
            PRIMARY KEY (stock_id, trade_date),
            FOREIGN KEY (stock_id) REFERENCES stocks(id)
        );
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks(symbol);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stocks_ticker ON stocks(ticker);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_stock_id ON daily_prices(stock_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_trade_date ON daily_prices(trade_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_stock_date ON daily_prices(stock_id, trade_date);")

    conn.commit()
    conn.close()
