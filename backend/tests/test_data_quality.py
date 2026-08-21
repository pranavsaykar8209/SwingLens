import sqlite3
import pytest
from backend.database.connection import get_db_connection, init_db
from backend.scripts.data_quality_report import (
    check_database_integrity,
    check_stock_universe,
    check_duplicate_candles,
    check_missing_values,
    check_ohlc_errors,
    check_volume_validation,
    check_date_consistency,
    check_suspicious_price_moves,
)
from backend.scripts.initialize_data import upsert_stock


@pytest.fixture
def sample_db(tmp_path):
    db_file = tmp_path / "test_quality.db"
    init_db(db_file)
    conn = get_db_connection(db_file)

    # Insert sample stock
    stock_id1 = upsert_stock(conn, {
        "symbol": "STOCKA",
        "ticker": "STOCKA.NS",
        "company_name": "Stock A",
        "exchange": "NSE",
        "series": "EQ",
    })

    stock_id2 = upsert_stock(conn, {
        "symbol": "STOCKB",
        "ticker": "STOCKB.NS",
        "company_name": "Stock B",
        "exchange": "NSE",
        "series": "EQ",
    })

    cursor = conn.cursor()

    # Valid data for STOCKA
    cursor.execute("""
        INSERT INTO daily_prices (stock_id, trade_date, open, high, low, close, adjusted_close, volume)
        VALUES
        (?, '2024-01-01', 100.0, 105.0, 95.0, 102.0, 102.0, 1000),
        (?, '2024-01-02', 102.0, 140.0, 101.0, 135.0, 135.0, 2000);  -- >25% jump (suspicious move warning)
    """, (stock_id1, stock_id1))

    # Data with errors for STOCKB
    cursor.execute("""
        INSERT INTO daily_prices (stock_id, trade_date, open, high, low, close, adjusted_close, volume)
        VALUES
        (?, '2024-01-01', 100.0, 90.0, 95.0, 92.0, 92.0, 1000);  -- Invalid high < low
    """, (stock_id2,))

    conn.commit()
    yield conn
    conn.close()


def test_database_integrity(sample_db):
    res = check_database_integrity(sample_db)
    assert res["is_valid"] is True
    assert res["missing_tables"] == []
    assert res["fk_errors_count"] == 0


def test_stock_universe(sample_db):
    res = check_stock_universe(sample_db)
    assert res["total_stocks"] == 2
    assert res["dup_symbols_count"] == 0
    assert res["dup_tickers_count"] == 0
    assert res["missing_symbols"] == 0


def test_duplicate_candles(sample_db):
    dup_count = check_duplicate_candles(sample_db)
    assert dup_count == 0


def test_ohlc_errors(sample_db):
    err_count, invalid_rows = check_ohlc_errors(sample_db)
    assert err_count == 1
    assert invalid_rows[0]["high"] < invalid_rows[0]["low"]


def test_volume_validation(sample_db):
    res = check_volume_validation(sample_db)
    assert res["negative_volume"] == 0
    assert res["zero_volume"] == 0
    assert res["missing_volume"] == 0


def test_date_consistency(sample_db):
    res = check_date_consistency(sample_db)
    assert res["overall_min_date"] == "2024-01-01"
    assert res["overall_max_date"] == "2024-01-02"


def test_suspicious_price_moves(sample_db):
    warnings = check_suspicious_price_moves(sample_db, threshold_pct=25.0)
    assert len(warnings) == 1
    assert warnings[0]["symbol"] == "STOCKA"
    assert warnings[0]["change_pct"] > 25.0
