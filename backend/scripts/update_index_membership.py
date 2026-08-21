import logging
from pathlib import Path
import sys

from backend.database.connection import get_db_connection, init_db, DEFAULT_DB_PATH
from backend.market_data.membership import update_index_constituents

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("update_index_membership")


def run_index_membership_update(db_path: Path = DEFAULT_DB_PATH, index_name: str = "NIFTY_NEXT_50") -> None:
    print("SwingLens Index Membership Update")
    print("=================================\n")

    init_db(db_path)
    conn = get_db_connection(db_path)

    res = update_index_constituents(conn, index_name=index_name)
    conn.close()

    print(f"Index: {res['index_name']}\n")
    print(f"Current constituents: {res['current_count']}")
    print(f"Already active      : {res['already_active_count']}")
    print(f"New members         : {res['new_members_count']}")
    print(f"Removed members     : {res['removed_members_count']}\n")

    if res["added_symbols"]:
        print("Added:")
        for sym in res["added_symbols"]:
            print(f"  + {sym}")
        print()
    else:
        print("Added: None\n")

    if res["removed_symbols"]:
        print("Removed:")
        for sym in res["removed_symbols"]:
            print(f"  - {sym}")
        print()
    else:
        print("Removed: None\n")

    print("Status: COMPLETE")
    print("=============================================")


if __name__ == "__main__":
    run_index_membership_update()
