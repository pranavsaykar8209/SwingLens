from datetime import datetime
import sqlite3
import pytest
import pandas as pd
from backend.database.connection import get_db_connection, init_db
from backend.scripts.initialize_data import upsert_stock, save_stock_prices


@pytest.fixture
def test_db_path(tmp_path):
    db_file = tmp_path / "test_swinglens.db"
    init_db(db_file)
    return db_file


@pytest.fixture
def memory_db(test_db_path):
    conn = get_db_connection(test_db_path)
    yield conn
    conn.close()


def test_init_db(tmp_path):
    db_file = tmp_path / "test_init.db"
    init_db(db_file)

    conn = get_db_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    assert "stocks" in tables
    assert "daily_prices" in tables

    # Verify indexes exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = [row[0] for row in cursor.fetchall()]
    assert "idx_stocks_symbol" in indexes
    assert "idx_daily_prices_stock_id" in indexes
    assert "idx_daily_prices_trade_date" in indexes
    assert "idx_daily_prices_stock_date" in indexes

    conn.close()


def test_stock_insertion_and_duplicate_prevention(memory_db):
    stock_info = {
        "symbol": "COALINDIA",
        "ticker": "COALINDIA.NS",
        "company_name": "Coal India Ltd.",
        "exchange": "NSE",
        "series": "EQ",
    }

    # 1. First Insertion
    stock_id1 = upsert_stock(memory_db, stock_info)
    assert stock_id1 is not None

    # 2. Duplicate Insertion (UPSERT check)
    stock_info_updated = {
        "symbol": "COALINDIA",
        "ticker": "COALINDIA.NS",
        "company_name": "Coal India Limited Updated",
        "exchange": "NSE",
        "series": "EQ",
    }
    stock_id2 = upsert_stock(memory_db, stock_info_updated)
    assert stock_id1 == stock_id2

    # Verify only 1 stock row exists and company_name was updated
    cursor = memory_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM stocks;")
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT company_name FROM stocks WHERE id = ?;", (stock_id1,))
    assert cursor.fetchone()[0] == "Coal India Limited Updated"


def test_daily_price_insertion_and_upsert(memory_db):
    stock_info = {
        "symbol": "TRENT",
        "ticker": "TRENT.NS",
        "company_name": "Trent Ltd.",
        "exchange": "NSE",
        "series": "EQ",
    }
    stock_id = upsert_stock(memory_db, stock_info)

    sample_df = pd.DataFrame([
        {
            "trade_date": "2024-01-01",
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 104.0,
            "adjusted_close": 104.0,
            "volume": 10000,
        },
        {
            "trade_date": "2024-01-02",
            "open": 104.0,
            "high": 108.0,
            "low": 103.0,
            "close": 107.0,
            "adjusted_close": 107.0,
            "volume": 15000,
        },
    ])

    # Initial Save
    inserted, updated = save_stock_prices(memory_db, stock_id, sample_df)
    memory_db.commit()

    assert inserted == 2
    assert updated == 0

    # UPSERT update test with revised close price for 2024-01-01 and new row for 2024-01-03
    updated_df = pd.DataFrame([
        {
            "trade_date": "2024-01-01",
            "open": 100.0,
            "high": 106.0,
            "low": 98.0,
            "close": 105.5,  # Modified close
            "adjusted_close": 105.5,
            "volume": 12000,
        },
        {
            "trade_date": "2024-01-03",
            "open": 107.0,
            "high": 110.0,
            "low": 106.0,
            "close": 109.0,
            "adjusted_close": 109.0,
            "volume": 8000,
        },
    ])

    inserted2, updated2 = save_stock_prices(memory_db, stock_id, updated_df)
    memory_db.commit()

    assert inserted2 == 1
    assert updated2 == 1

    cursor = memory_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_prices WHERE stock_id = ?;", (stock_id,))
    assert cursor.fetchone()[0] == 3

    cursor.execute("SELECT close FROM daily_prices WHERE stock_id = ? AND trade_date = '2024-01-01';", (stock_id,))
    assert cursor.fetchone()[0] == 105.5
