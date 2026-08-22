import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

DEFAULT_DB_PATH = Path("data/swinglens.db")


def get_db_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """
    Establishes and returns a connection to the SQLite database.
    Ensures foreign keys are enabled.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    db_path_obj = Path(db_path)
    if str(db_path) != ":memory:":
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path_obj))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """
    Initializes the database schema including `stocks`, `daily_prices`, and `index_memberships`
    tables and their required indexes.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

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

    # Table: index_memberships
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS index_memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            index_name TEXT NOT NULL,
            stock_id INTEGER NOT NULL,
            valid_from DATE NOT NULL,
            valid_to DATE NULL,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY (stock_id) REFERENCES stocks(id),
            UNIQUE(index_name, stock_id, valid_from)
        );
    """)

    # Table: daily_scan_runs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date DATE NOT NULL,
            universe TEXT NOT NULL,
            strategy TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            stocks_processed INTEGER DEFAULT 0,
            stocks_updated INTEGER DEFAULT 0,
            rows_downloaded INTEGER DEFAULT 0,
            buy_count INTEGER DEFAULT 0,
            watch_count INTEGER DEFAULT 0,
            hold_count INTEGER DEFAULT 0,
            skipped_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Table: watchlist_setups. Values are a snapshot of the setup when saved;
    # they are never recalculated from later strategy runs.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_setups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL,
            signal_date DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'TRIGGERED', 'EXPIRED', 'CANCELLED')),
            aggregated_score INTEGER NOT NULL CHECK (aggregated_score BETWEEN 1 AND 5),
            signal_strength TEXT NOT NULL
                CHECK (signal_strength IN ('WEAK', 'MODERATE', 'STRONG', 'VERY_STRONG')),
            buy_strategies TEXT NOT NULL,
            entry_price REAL NOT NULL CHECK (entry_price > 0),
            stop_loss REAL NOT NULL CHECK (stop_loss > 0 AND stop_loss < entry_price),
            target_price REAL NOT NULL CHECK (target_price > entry_price),
            risk_reward REAL NOT NULL CHECK (risk_reward > 0),
            best_strategy_name TEXT NOT NULL,
            outcome TEXT NOT NULL DEFAULT 'PENDING'
                CHECK (outcome IN ('PENDING', 'ENTRY_REACHED', 'TARGET_HIT', 'STOP_HIT', 'EXPIRED', 'NO_ENTRY', 'AMBIGUOUS')),
            entry_date DATE,
            exit_date DATE,
            exit_price REAL,
            holding_days INTEGER,
            mfe REAL,
            mfe_r REAL,
            mae REAL,
            mae_r REAL,
            realized_r REAL,
            outcome_checked_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stock_id) REFERENCES stocks(id)
        );
    """)

    # SQLite supports only limited ALTER TABLE operations. Add fields for
    # databases created before outcome tracking without changing snapshots.
    watchlist_columns = {row[1] for row in cursor.execute("PRAGMA table_info(watchlist_setups)")}
    for column, definition in {
        "outcome": "TEXT NOT NULL DEFAULT 'PENDING'",
        "entry_date": "DATE",
        "exit_date": "DATE",
        "exit_price": "REAL",
        "holding_days": "INTEGER",
        "mfe": "REAL",
        "mfe_r": "REAL",
        "mae": "REAL",
        "mae_r": "REAL",
        "realized_r": "REAL",
        "outcome_checked_at": "DATETIME",
    }.items():
        if column not in watchlist_columns:
            cursor.execute(f"ALTER TABLE watchlist_setups ADD COLUMN {column} {definition}")

    # Table: daily_scan_results. Immutable persisted snapshots of daily multi-strategy rankings.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_run_id INTEGER,
            scan_date DATE NOT NULL,
            stock_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            rank INTEGER NOT NULL,
            score INTEGER NOT NULL,
            strength TEXT NOT NULL,
            tier TEXT NOT NULL,
            buy_count INTEGER NOT NULL,
            strategies_evaluated INTEGER NOT NULL,
            strategies_total INTEGER NOT NULL DEFAULT 5,
            buy_strategies TEXT NOT NULL DEFAULT '[]',
            hold_strategies TEXT NOT NULL DEFAULT '[]',
            error_strategies TEXT NOT NULL DEFAULT '[]',
            best_strategy_name TEXT,
            entry_price REAL,
            stop_loss REAL,
            target_price REAL,
            risk_reward REAL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scan_run_id) REFERENCES daily_scan_runs(id),
            FOREIGN KEY (stock_id) REFERENCES stocks(id),
            UNIQUE(scan_date, stock_id)
        );
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks(symbol);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stocks_ticker ON stocks(ticker);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_stock_id ON daily_prices(stock_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_trade_date ON daily_prices(trade_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_stock_date ON daily_prices(stock_id, trade_date);")

    # Index memberships indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_index_memberships_index_name ON index_memberships(index_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_index_memberships_stock_id ON index_memberships(stock_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_index_memberships_valid_from ON index_memberships(valid_from);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_index_memberships_valid_to ON index_memberships(valid_to);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_index_memberships_lookup ON index_memberships(index_name, valid_from, valid_to);")

    # Daily scan runs indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_scan_runs_lookup ON daily_scan_runs(scan_date, universe, strategy, status);")

    # Daily scan results indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_scan_results_date ON daily_scan_results(scan_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_scan_results_run ON daily_scan_results(scan_run_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_scan_results_stock ON daily_scan_results(stock_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_scan_results_symbol ON daily_scan_results(symbol);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_scan_results_date_rank ON daily_scan_results(scan_date, rank);")

    # Watchlist setup indexes. The partial unique index prevents duplicate
    # active records while retaining completed setup history.
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_setups_status ON watchlist_setups(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_setups_stock_id ON watchlist_setups(stock_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_setups_signal_date ON watchlist_setups(signal_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_setups_created_at ON watchlist_setups(created_at);")
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_watchlist_setups_active_stock
        ON watchlist_setups(stock_id) WHERE status = 'ACTIVE';
    """)

    conn.commit()
    conn.close()


def is_index_member(
    conn: sqlite3.Connection,
    index_name: str,
    stock_id: int,
    trade_date: str,
) -> bool:
    """
    Checks if stock_id was an active constituent of index_name on trade_date.
    Condition: valid_from <= trade_date AND (valid_to IS NULL OR trade_date <= valid_to)
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1 FROM index_memberships
        WHERE index_name = ?
          AND stock_id = ?
          AND valid_from <= ?
          AND (valid_to IS NULL OR ? <= valid_to)
        LIMIT 1;
        """,
        (index_name, stock_id, trade_date, trade_date),
    )
    return cursor.fetchone() is not None
