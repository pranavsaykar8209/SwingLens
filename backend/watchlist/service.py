"""Service layer for local, immutable watchlist setup snapshots."""

import json
import sqlite3
from pathlib import Path

from backend.database.connection import DEFAULT_DB_PATH, get_db_connection, init_db

from .models import WatchlistSetup, WatchlistSetupCreate, WatchlistStatus


class WatchlistNotFoundError(ValueError):
    pass


class DuplicateActiveSetupError(ValueError):
    pass


class InvalidStatusTransitionError(ValueError):
    pass


class WatchlistService:
    """Persist and retrieve setup snapshots without invoking any strategy logic."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        init_db(db_path)

    @staticmethod
    def _to_model(row: sqlite3.Row) -> WatchlistSetup:
        return WatchlistSetup(
            id=row["id"], symbol=row["symbol"], company_name=row["company_name"],
            signal_date=row["signal_date"], created_at=row["created_at"], status=row["status"],
            aggregated_score=row["aggregated_score"], signal_strength=row["signal_strength"],
            buy_strategies=json.loads(row["buy_strategies"]), entry_price=row["entry_price"],
            stop_loss=row["stop_loss"], target_price=row["target_price"],
            risk_reward=row["risk_reward"], best_strategy_name=row["best_strategy_name"],
            outcome=row["outcome"], entry_date=row["entry_date"], exit_date=row["exit_date"],
            exit_price=row["exit_price"], holding_days=row["holding_days"], mfe=row["mfe"],
            mfe_r=row["mfe_r"], mae=row["mae"], mae_r=row["mae_r"], realized_r=row["realized_r"],
            outcome_checked_at=row["outcome_checked_at"],
        )

    def _get_by_id(self, conn: sqlite3.Connection, setup_id: int) -> WatchlistSetup:
        row = conn.execute("""
            SELECT w.*, s.symbol, s.company_name
            FROM watchlist_setups w JOIN stocks s ON s.id = w.stock_id
            WHERE w.id = ?
        """, (setup_id,)).fetchone()
        if row is None:
            raise WatchlistNotFoundError(f"Watchlist setup {setup_id} was not found")
        return self._to_model(row)

    def create(self, setup: WatchlistSetupCreate) -> WatchlistSetup:
        conn = get_db_connection(self.db_path)
        try:
            stock = conn.execute("SELECT id FROM stocks WHERE symbol = ?", (setup.symbol.upper(),)).fetchone()
            if stock is None:
                raise WatchlistNotFoundError(f"Stock symbol '{setup.symbol.upper()}' not found in database")
            try:
                cursor = conn.execute("""
                    INSERT INTO watchlist_setups (
                        stock_id, signal_date, aggregated_score, signal_strength, buy_strategies,
                        entry_price, stop_loss, target_price, risk_reward, best_strategy_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stock["id"], setup.signal_date.isoformat(), setup.aggregated_score,
                    setup.signal_strength.value, json.dumps(setup.buy_strategies), setup.entry_price,
                    setup.stop_loss, setup.target_price, setup.risk_reward, setup.best_strategy_name,
                ))
            except sqlite3.IntegrityError as error:
                if "UNIQUE constraint failed: watchlist_setups.stock_id" in str(error):
                    raise DuplicateActiveSetupError(
                        f"An ACTIVE watchlist setup already exists for '{setup.symbol.upper()}'"
                    ) from error
                raise
            conn.commit()
            return self._get_by_id(conn, cursor.lastrowid)
        finally:
            conn.close()

    def list(self, status: WatchlistStatus = WatchlistStatus.ACTIVE) -> list[WatchlistSetup]:
        conn = get_db_connection(self.db_path)
        try:
            rows = conn.execute("""
                SELECT w.*, s.symbol, s.company_name
                FROM watchlist_setups w JOIN stocks s ON s.id = w.stock_id
                WHERE w.status = ?
                ORDER BY w.created_at DESC, w.id DESC
            """, (status.value,)).fetchall()
            return [self._to_model(row) for row in rows]
        finally:
            conn.close()

    def get(self, setup_id: int) -> WatchlistSetup:
        conn = get_db_connection(self.db_path)
        try:
            return self._get_by_id(conn, setup_id)
        finally:
            conn.close()

    def update_status(self, setup_id: int, status: WatchlistStatus) -> WatchlistSetup:
        if status == WatchlistStatus.ACTIVE:
            raise InvalidStatusTransitionError("Watchlist setups cannot transition back to ACTIVE")
        conn = get_db_connection(self.db_path)
        try:
            current = self._get_by_id(conn, setup_id)
            if current.status != WatchlistStatus.ACTIVE:
                raise InvalidStatusTransitionError(
                    f"Only ACTIVE setups can transition; setup {setup_id} is {current.status.value}"
                )
            conn.execute("UPDATE watchlist_setups SET status = ? WHERE id = ?", (status.value, setup_id))
            conn.commit()
            return self._get_by_id(conn, setup_id)
        finally:
            conn.close()
