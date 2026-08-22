"""Historical daily-candle outcome evaluation for saved BUY setup snapshots."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from backend.database.connection import DEFAULT_DB_PATH, get_db_connection, init_db

from .models import WatchlistOutcome, WatchlistSetup
from .service import WatchlistNotFoundError, WatchlistService


FINAL_OUTCOMES = {
    WatchlistOutcome.TARGET_HIT, WatchlistOutcome.STOP_HIT,
    WatchlistOutcome.AMBIGUOUS, WatchlistOutcome.EXPIRED, WatchlistOutcome.NO_ENTRY,
}


class WatchlistOutcomeService:
    """Evaluate only candles strictly after a setup's signal date.

    Daily OHLC does not reveal intraday ordering. If the entry candle touches a
    stop or target, or a later candle touches both stop and target, the result
    is AMBIGUOUS rather than an assumed fill sequence.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, max_holding_days: int = 20):
        if max_holding_days <= 0:
            raise ValueError("max_holding_days must be positive")
        self.db_path = db_path
        self.max_holding_days = max_holding_days
        init_db(db_path)
        self.watchlist = WatchlistService(db_path)

    def evaluate(self, setup_id: int) -> WatchlistSetup:
        setup = self.watchlist.get(setup_id)
        if setup.outcome in FINAL_OUTCOMES:
            return setup

        conn = get_db_connection(self.db_path)
        try:
            rows = conn.execute("""
                SELECT p.trade_date, p.high, p.low
                FROM daily_prices p
                JOIN watchlist_setups w ON w.stock_id = p.stock_id
                WHERE w.id = ? AND p.trade_date > w.signal_date
                ORDER BY p.trade_date ASC
            """, (setup_id,)).fetchall()
            values = self._evaluate_rows(setup, rows)
            # Repeated evaluation with no newly observable outcome/metrics is
            # idempotent, including its reported check timestamp. Unresolved
            # setups are still updated when later candles change any value.
            if (
                setup.outcome_checked_at is not None
                and all(getattr(setup, key) == value for key, value in values.items())
            ):
                return setup
            values["outcome_checked_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
            columns = ", ".join(f"{key} = ?" for key in values)
            conn.execute(
                f"UPDATE watchlist_setups SET {columns} WHERE id = ?",
                [self._db_value(value) for value in values.values()] + [setup_id],
            )
            conn.commit()
        finally:
            conn.close()
        return self.watchlist.get(setup_id)

    @staticmethod
    def _db_value(value):
        return value.value if isinstance(value, WatchlistOutcome) else value

    def _evaluate_rows(self, setup: WatchlistSetup, rows: list[sqlite3.Row]) -> dict:
        base = dict(
            outcome=WatchlistOutcome.PENDING, entry_date=None, exit_date=None, exit_price=None,
            holding_days=None, mfe=None, mfe_r=None, mae=None, mae_r=None, realized_r=None,
        )
        entry_index = next((i for i, row in enumerate(rows) if row["low"] <= setup.entry_price <= row["high"]), None)
        if entry_index is None:
            if len(rows) >= self.max_holding_days:
                base["outcome"] = WatchlistOutcome.NO_ENTRY
            return base

        entry_row = rows[entry_index]
        after_entry = rows[entry_index:]
        risk = setup.entry_price - setup.stop_loss
        base.update(
            outcome=WatchlistOutcome.ENTRY_REACHED, entry_date=entry_row["trade_date"],
        )

        def add_excursions(candles: list[sqlite3.Row]) -> None:
            mfe = max(row["high"] for row in candles) - setup.entry_price
            mae = max(0.0, setup.entry_price - min(row["low"] for row in candles))
            base.update(mfe=mfe, mfe_r=mfe / risk, mae=mae, mae_r=mae / risk)

        # An entry-day stop/target touch has an unknowable order versus entry.
        if entry_row["high"] >= setup.target_price or entry_row["low"] <= setup.stop_loss:
            base.update(outcome=WatchlistOutcome.AMBIGUOUS, exit_date=entry_row["trade_date"], holding_days=0)
            add_excursions([entry_row])
            return base

        for holding_days, row in enumerate(rows[entry_index + 1:], start=1):
            hit_target = row["high"] >= setup.target_price
            hit_stop = row["low"] <= setup.stop_loss
            if hit_target and hit_stop:
                base.update(outcome=WatchlistOutcome.AMBIGUOUS, exit_date=row["trade_date"], holding_days=holding_days)
                add_excursions(after_entry[:holding_days + 1])
                return base
            if hit_target:
                base.update(
                    outcome=WatchlistOutcome.TARGET_HIT, exit_date=row["trade_date"],
                    exit_price=setup.target_price, holding_days=holding_days,
                    realized_r=(setup.target_price - setup.entry_price) / risk,
                )
                add_excursions(after_entry[:holding_days + 1])
                return base
            if hit_stop:
                base.update(
                    outcome=WatchlistOutcome.STOP_HIT, exit_date=row["trade_date"],
                    exit_price=setup.stop_loss, holding_days=holding_days, realized_r=-1.0,
                )
                add_excursions(after_entry[:holding_days + 1])
                return base
            if holding_days >= self.max_holding_days:
                base.update(outcome=WatchlistOutcome.EXPIRED, exit_date=row["trade_date"], holding_days=holding_days)
                add_excursions(after_entry[:holding_days + 1])
                return base
        add_excursions(after_entry)
        return base
