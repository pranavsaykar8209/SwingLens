from datetime import datetime
import logging
import sqlite3
from typing import Dict, Any, List, Optional

from backend.market_data.universe import fetch_nifty_next_50_constituents
from backend.scripts.initialize_data import upsert_stock

logger = logging.getLogger(__name__)


def update_index_constituents(
    conn: sqlite3.Connection,
    index_name: str = "NIFTY_NEXT_50",
    constituents: Optional[List[Dict[str, Any]]] = None,
    effective_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Updates the `index_memberships` table for a given index.

    - Adds newly discovered constituents with valid_from = effective_date (default today), valid_to = NULL.
    - Closes memberships for stocks no longer present by setting valid_to = effective_date.
    - Does not modify existing identical active memberships.
    """
    today_str = effective_date or datetime.now().strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat()

    if constituents is None:
        constituents = fetch_nifty_next_50_constituents()

    # 1. Upsert all constituents in stocks table and map symbol -> stock_id
    current_symbol_to_id: Dict[str, int] = {}
    for item in constituents:
        stock_id = upsert_stock(conn, item)
        current_symbol_to_id[item["symbol"]] = stock_id

    # 2. Get active membership records in DB (valid_to IS NULL)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.id, m.stock_id, s.symbol
        FROM index_memberships m
        JOIN stocks s ON m.stock_id = s.id
        WHERE m.index_name = ? AND m.valid_to IS NULL;
        """,
        (index_name,),
    )
    active_db_rows = cursor.fetchall()
    active_symbol_to_row = {row["symbol"]: dict(row) for row in active_db_rows}

    current_symbols = set(current_symbol_to_id.keys())
    active_symbols = set(active_symbol_to_row.keys())

    already_active_symbols = current_symbols.intersection(active_symbols)
    new_symbols = current_symbols - active_symbols
    removed_symbols = active_symbols - current_symbols

    added_list: List[str] = []
    removed_list: List[str] = []

    # 3. Add new membership records
    for sym in sorted(new_symbols):
        stock_id = current_symbol_to_id[sym]
        cursor.execute(
            """
            INSERT INTO index_memberships (index_name, stock_id, valid_from, valid_to, created_at, updated_at)
            VALUES (?, ?, ?, NULL, ?, ?)
            ON CONFLICT(index_name, stock_id, valid_from) DO UPDATE SET
                valid_to = NULL,
                updated_at = excluded.updated_at;
            """,
            (index_name, stock_id, today_str, now_iso, now_iso),
        )
        added_list.append(sym)

    # 4. Close removed membership records
    for sym in sorted(removed_symbols):
        membership_id = active_symbol_to_row[sym]["id"]
        cursor.execute(
            """
            UPDATE index_memberships
            SET valid_to = ?, updated_at = ?
            WHERE id = ?;
            """,
            (today_str, now_iso, membership_id),
        )
        removed_list.append(sym)

    if added_list or removed_list:
        conn.commit()

    return {
        "index_name": index_name,
        "current_count": len(constituents),
        "already_active_count": len(already_active_symbols),
        "new_members_count": len(added_list),
        "removed_members_count": len(removed_list),
        "added_symbols": added_list,
        "removed_symbols": removed_list,
    }
