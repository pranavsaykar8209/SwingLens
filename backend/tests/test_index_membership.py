from datetime import datetime, timedelta
from unittest.mock import patch
import pytest
from backend.database.connection import get_db_connection, init_db, is_index_member
from backend.market_data.membership import update_index_constituents
from backend.scripts.initialize_data import upsert_stock


@pytest.fixture
def memory_db(tmp_path):
    db_file = tmp_path / "test_membership.db"
    init_db(db_file)
    conn = get_db_connection(db_file)
    yield conn
    conn.close()


def test_create_index_memberships_table(memory_db):
    cursor = memory_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='index_memberships';")
    assert cursor.fetchone() is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_index_memberships%';")
    indexes = [r[0] for r in cursor.fetchall()]
    assert "idx_index_memberships_index_name" in indexes
    assert "idx_index_memberships_stock_id" in indexes
    assert "idx_index_memberships_lookup" in indexes


def test_add_membership(memory_db):
    stock_id = upsert_stock(memory_db, {
        "symbol": "ABB",
        "ticker": "ABB.NS",
        "company_name": "ABB India Ltd.",
        "exchange": "NSE",
        "series": "EQ",
    })

    cursor = memory_db.cursor()
    cursor.execute("""
        INSERT INTO index_memberships (index_name, stock_id, valid_from, valid_to, created_at, updated_at)
        VALUES ('NIFTY_NEXT_50', ?, '2024-01-01', NULL, '2024-01-01', '2024-01-01');
    """, (stock_id,))
    memory_db.commit()

    assert is_index_member(memory_db, "NIFTY_NEXT_50", stock_id, "2024-01-01") is True
    assert is_index_member(memory_db, "NIFTY_NEXT_50", stock_id, "2024-06-01") is True


def test_prevent_duplicate_memberships(memory_db):
    stock_id = upsert_stock(memory_db, {
        "symbol": "DLF",
        "ticker": "DLF.NS",
        "company_name": "DLF Ltd.",
        "exchange": "NSE",
        "series": "EQ",
    })

    cursor = memory_db.cursor()
    cursor.execute("""
        INSERT INTO index_memberships (index_name, stock_id, valid_from, valid_to, created_at, updated_at)
        VALUES ('NIFTY_NEXT_50', ?, '2024-01-01', NULL, '2024-01-01', '2024-01-01');
    """, (stock_id,))
    memory_db.commit()

    with pytest.raises(Exception):
        # Unique constraint on (index_name, stock_id, valid_from) should fail duplicate insert
        cursor.execute("""
            INSERT INTO index_memberships (index_name, stock_id, valid_from, valid_to, created_at, updated_at)
            VALUES ('NIFTY_NEXT_50', ?, '2024-01-01', NULL, '2024-01-01', '2024-01-01');
        """, (stock_id,))


def test_detect_active_membership(memory_db):
    stock_id = upsert_stock(memory_db, {
        "symbol": "GAIL",
        "ticker": "GAIL.NS",
        "company_name": "GAIL Ltd.",
        "exchange": "NSE",
        "series": "EQ",
    })

    cursor = memory_db.cursor()
    cursor.execute("""
        INSERT INTO index_memberships (index_name, stock_id, valid_from, valid_to, created_at, updated_at)
        VALUES ('NIFTY_NEXT_50', ?, '2024-01-01', NULL, '2024-01-01', '2024-01-01');
    """, (stock_id,))
    memory_db.commit()

    assert is_index_member(memory_db, "NIFTY_NEXT_50", stock_id, "2024-05-01") is True


def test_detect_inactive_membership(memory_db):
    stock_id = upsert_stock(memory_db, {
        "symbol": "OLDSTOCK",
        "ticker": "OLDSTOCK.NS",
        "company_name": "Old Stock Ltd.",
        "exchange": "NSE",
        "series": "EQ",
    })

    cursor = memory_db.cursor()
    cursor.execute("""
        INSERT INTO index_memberships (index_name, stock_id, valid_from, valid_to, created_at, updated_at)
        VALUES ('NIFTY_NEXT_50', ?, '2022-01-01', '2023-12-31', '2022-01-01', '2023-12-31');
    """, (stock_id,))
    memory_db.commit()

    # Active during 2022-2023
    assert is_index_member(memory_db, "NIFTY_NEXT_50", stock_id, "2023-06-01") is True
    # Inactive in 2024
    assert is_index_member(memory_db, "NIFTY_NEXT_50", stock_id, "2024-01-01") is False
    # Inactive prior to 2022
    assert is_index_member(memory_db, "NIFTY_NEXT_50", stock_id, "2021-12-31") is False


def test_membership_null_valid_to(memory_db):
    stock_id = upsert_stock(memory_db, {
        "symbol": "TRENT",
        "ticker": "TRENT.NS",
        "company_name": "Trent Ltd.",
        "exchange": "NSE",
        "series": "EQ",
    })

    cursor = memory_db.cursor()
    cursor.execute("""
        INSERT INTO index_memberships (index_name, stock_id, valid_from, valid_to, created_at, updated_at)
        VALUES ('NIFTY_NEXT_50', ?, '2024-01-01', NULL, '2024-01-01', '2024-01-01');
    """, (stock_id,))
    memory_db.commit()

    cursor.execute("SELECT valid_to FROM index_memberships WHERE stock_id = ?;", (stock_id,))
    assert cursor.fetchone()[0] is None
    assert is_index_member(memory_db, "NIFTY_NEXT_50", stock_id, "2030-01-01") is True


def test_membership_with_valid_to(memory_db):
    stock_id = upsert_stock(memory_db, {
        "symbol": "CLOSEDSTOCK",
        "ticker": "CLOSEDSTOCK.NS",
        "company_name": "Closed Stock",
        "exchange": "NSE",
        "series": "EQ",
    })

    cursor = memory_db.cursor()
    cursor.execute("""
        INSERT INTO index_memberships (index_name, stock_id, valid_from, valid_to, created_at, updated_at)
        VALUES ('NIFTY_NEXT_50', ?, '2021-01-01', '2023-01-01', '2021-01-01', '2023-01-01');
    """, (stock_id,))
    memory_db.commit()

    assert is_index_member(memory_db, "NIFTY_NEXT_50", stock_id, "2022-01-01") is True
    assert is_index_member(memory_db, "NIFTY_NEXT_50", stock_id, "2023-01-02") is False


def test_update_idempotence(memory_db):
    mock_constituents = [
        {"symbol": "STOCK1", "ticker": "STOCK1.NS", "company_name": "Stock 1", "exchange": "NSE", "series": "EQ"},
        {"symbol": "STOCK2", "ticker": "STOCK2.NS", "company_name": "Stock 2", "exchange": "NSE", "series": "EQ"},
    ]

    # Run 1
    res1 = update_index_constituents(memory_db, index_name="NIFTY_NEXT_50", constituents=mock_constituents, effective_date="2024-01-01")
    assert res1["new_members_count"] == 2
    assert res1["removed_members_count"] == 0

    # Run 2 with identical constituents
    res2 = update_index_constituents(memory_db, index_name="NIFTY_NEXT_50", constituents=mock_constituents, effective_date="2024-01-02")
    assert res2["already_active_count"] == 2
    assert res2["new_members_count"] == 0
    assert res2["removed_members_count"] == 0


def test_removed_member_gets_valid_to(memory_db):
    initial_constituents = [
        {"symbol": "STOCK1", "ticker": "STOCK1.NS", "company_name": "Stock 1", "exchange": "NSE", "series": "EQ"},
        {"symbol": "STOCK2", "ticker": "STOCK2.NS", "company_name": "Stock 2", "exchange": "NSE", "series": "EQ"},
    ]
    update_index_constituents(memory_db, index_name="NIFTY_NEXT_50", constituents=initial_constituents, effective_date="2024-01-01")

    # Remove STOCK2 in second update
    revised_constituents = [
        {"symbol": "STOCK1", "ticker": "STOCK1.NS", "company_name": "Stock 1", "exchange": "NSE", "series": "EQ"},
    ]
    res2 = update_index_constituents(memory_db, index_name="NIFTY_NEXT_50", constituents=revised_constituents, effective_date="2024-06-01")

    assert res2["removed_members_count"] == 1
    assert "STOCK2" in res2["removed_symbols"]

    # Verify STOCK2 has valid_to = '2024-06-01'
    cursor = memory_db.cursor()
    cursor.execute("""
        SELECT m.valid_to FROM index_memberships m
        JOIN stocks s ON m.stock_id = s.id
        WHERE s.symbol = 'STOCK2';
    """)
    assert cursor.fetchone()[0] == "2024-06-01"


def test_newly_added_member_creates_record(memory_db):
    initial_constituents = [
        {"symbol": "STOCK1", "ticker": "STOCK1.NS", "company_name": "Stock 1", "exchange": "NSE", "series": "EQ"},
    ]
    update_index_constituents(memory_db, index_name="NIFTY_NEXT_50", constituents=initial_constituents, effective_date="2024-01-01")

    # Add STOCK3 in second update
    revised_constituents = [
        {"symbol": "STOCK1", "ticker": "STOCK1.NS", "company_name": "Stock 1", "exchange": "NSE", "series": "EQ"},
        {"symbol": "STOCK3", "ticker": "STOCK3.NS", "company_name": "Stock 3", "exchange": "NSE", "series": "EQ"},
    ]
    res2 = update_index_constituents(memory_db, index_name="NIFTY_NEXT_50", constituents=revised_constituents, effective_date="2024-06-01")

    assert res2["new_members_count"] == 1
    assert "STOCK3" in res2["added_symbols"]

    cursor = memory_db.cursor()
    cursor.execute("""
        SELECT m.valid_from, m.valid_to FROM index_memberships m
        JOIN stocks s ON m.stock_id = s.id
        WHERE s.symbol = 'STOCK3';
    """)
    row = cursor.fetchone()
    assert row[0] == "2024-06-01"
    assert row[1] is None
