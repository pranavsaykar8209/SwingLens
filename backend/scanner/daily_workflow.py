from datetime import datetime
import logging
import sqlite3
import threading
from typing import Any, Dict, Optional

from backend.database.connection import DEFAULT_DB_PATH, get_db_connection, init_db
from backend.market_data.validator import validate_ohlcv_dataframe
from backend.ranking.ranker import DailySignalRanker
from backend.ranking.storage import persist_daily_scan_ranking
from backend.scanner import MarketScanner, ScanSummary
from backend.scripts.update_market_data import run_market_data_update

logger = logging.getLogger(__name__)

# Thread-safe lock protecting daily scan workflow execution
_SCAN_WORKFLOW_LOCK = threading.Lock()


def get_latest_market_date(conn: sqlite3.Connection) -> Optional[str]:
    """Retrieves the latest available trade_date from daily_prices table."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(trade_date) FROM daily_prices;")
    row = cursor.fetchone()
    if row and row[0]:
        return str(row[0])
    return None


def get_daily_scan_status(
    universe: str = "NIFTY_NEXT_50",
    strategy: str = "ema_pullback",
    db_path: Any = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Determines whether today's daily market scan workflow has completed successfully.
    Queries `daily_scan_runs` and `daily_scan_results` tables for status records.
    """
    # Ensure database schema is initialized
    init_db(db_path)

    conn = get_db_connection(db_path)
    try:
        latest_date = get_latest_market_date(conn)
        today_str = datetime.now().strftime("%Y-%m-%d")
        target_date = latest_date or today_str

        cursor = conn.cursor()

        # Check if daily_scan_results already has completed results for this target date
        cursor.execute(
            """
            SELECT COUNT(id) as result_count,
                   SUM(CASE WHEN buy_count > 0 THEN 1 ELSE 0 END) as buy_count
            FROM daily_scan_results
            WHERE scan_date = ?;
            """,
            (target_date,),
        )
        res_row = cursor.fetchone()
        # If daily_scan_results has rows for this date, the multi-strategy ranking snapshot is ready.
        if res_row and res_row["result_count"] > 0:
            cursor.execute(
                """
                SELECT completed_at FROM daily_scan_runs
                WHERE scan_date = ? AND status = 'COMPLETED'
                ORDER BY id DESC LIMIT 1;
                """,
                (target_date,),
            )
            run_row = cursor.fetchone()
            completed_at = run_row["completed_at"] if run_row else None

            return {
                "scan_date": target_date,
                "already_completed": True,
                "status": "COMPLETED",
                "latest_market_date": target_date,
                "last_completed_at": completed_at,
                "buy_count": res_row["buy_count"] or 0,
                "watch_count": 0,
                "hold_count": res_row["result_count"] - (res_row["buy_count"] or 0),
                "skipped_count": 0,
                "error_message": None,
            }

        # Check daily_scan_runs for completed run
        cursor.execute(
            """
            SELECT * FROM daily_scan_runs
            WHERE scan_date = ? AND universe = ? AND status = 'COMPLETED'
            ORDER BY id DESC LIMIT 1;
            """,
            (target_date, universe),
        )
        completed_row = cursor.fetchone()
        if completed_row:
            return {
                "scan_date": completed_row["scan_date"],
                "already_completed": True,
                "status": "COMPLETED",
                "latest_market_date": target_date,
                "last_completed_at": completed_row["completed_at"],
                "buy_count": completed_row["buy_count"],
                "watch_count": completed_row["watch_count"],
                "hold_count": completed_row["hold_count"],
                "skipped_count": completed_row["skipped_count"],
                "error_message": None,
            }

        # Check if there is an in-progress scan
        cursor.execute(
            """
            SELECT * FROM daily_scan_runs
            WHERE scan_date = ? AND universe = ? AND status = 'RUNNING'
            ORDER BY id DESC LIMIT 1;
            """,
            (target_date, universe),
        )
        running_row = cursor.fetchone()
        if running_row or _SCAN_WORKFLOW_LOCK.locked():
            return {
                "scan_date": target_date,
                "already_completed": False,
                "status": "RUNNING",
                "latest_market_date": target_date,
                "last_completed_at": None,
                "buy_count": 0,
                "watch_count": 0,
                "hold_count": 0,
                "skipped_count": 0,
                "error_message": None,
            }

        # Check if latest scan failed
        cursor.execute(
            """
            SELECT * FROM daily_scan_runs
            WHERE scan_date = ? AND universe = ? AND status = 'FAILED'
            ORDER BY id DESC LIMIT 1;
            """,
            (target_date, universe),
        )
        failed_row = cursor.fetchone()
        if failed_row:
            return {
                "scan_date": target_date,
                "already_completed": False,
                "status": "FAILED",
                "latest_market_date": target_date,
                "last_completed_at": None,
                "buy_count": 0,
                "watch_count": 0,
                "hold_count": 0,
                "skipped_count": 0,
                "error_message": failed_row["error_message"],
            }

        return {
            "scan_date": target_date,
            "already_completed": False,
            "status": "NOT_RUN",
            "latest_market_date": target_date,
            "last_completed_at": None,
            "buy_count": 0,
            "watch_count": 0,
            "hold_count": 0,
            "skipped_count": 0,
            "error_message": None,
        }
    finally:
        conn.close()


def run_daily_scan_workflow(
    universe: str = "NIFTY_NEXT_50",
    strategy: str = "ema_pullback",
    force: bool = False,
    db_path: Any = DEFAULT_DB_PATH,
) -> ScanSummary:
    """
    Executes the daily market scan workflow idempotently:
    1. If force=False and today's scan is COMPLETED, returns existing results immediately.
    2. Uses thread lock to prevent concurrent scan executions.
    3. Executes incremental market data update & data validation.
    4. Runs multi-strategy ranker across universe and persists snapshots to daily_scan_results.
    5. Records COMPLETED or FAILED in daily_scan_runs.
    """
    init_db(db_path)

    if not force:
        status_info = get_daily_scan_status(universe=universe, strategy=strategy, db_path=db_path)
        if status_info["already_completed"]:
            logger.info(
                f"Daily scan for {universe} already completed on {status_info['scan_date']}. Returning existing results."
            )
            scanner = MarketScanner()
            return scanner.scan_summary(index_name=universe, strategy_name=strategy, db_path=db_path)

    # Acquire concurrency lock
    if not _SCAN_WORKFLOW_LOCK.acquire(blocking=True, timeout=10.0):
        raise RuntimeError("Another daily market scan is currently executing. Please try again shortly.")

    run_id: Optional[int] = None
    conn = get_db_connection(db_path)
    try:
        latest_date = get_latest_market_date(conn)
        today_str = datetime.now().strftime("%Y-%m-%d")
        target_date = latest_date or today_str

        if not force:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM daily_scan_runs
                WHERE scan_date = ? AND universe = ? AND status = 'COMPLETED'
                ORDER BY id DESC LIMIT 1;
                """,
                (target_date, universe),
            )
            if cursor.fetchone():
                conn.close()
                scanner = MarketScanner()
                return scanner.scan_summary(index_name=universe, strategy_name=strategy, db_path=db_path)

        started_at = datetime.now().isoformat()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO daily_scan_runs (
                scan_date, universe, strategy, status, started_at, created_at, updated_at
            ) VALUES (?, ?, ?, 'RUNNING', ?, datetime('now'), datetime('now'));
            """,
            (target_date, universe, strategy, started_at),
        )
        run_id = cursor.lastrowid
        conn.commit()

        # Step 1: Incremental market data update (never re-downloads full history)
        logger.info(f"Executing incremental market data update for {universe}...")
        run_market_data_update(db_path=db_path)

        # Step 2: Data Validation completed during update
        logger.info(f"Incremental data update and validation complete for {universe}.")

        # Step 3: Run Multi-Strategy Daily Signal Ranker over the entire universe
        logger.info(f"Executing multi-strategy daily ranking pipeline for {universe}...")
        ranker = DailySignalRanker()
        ranking = ranker.run(index_name=universe, db_path=db_path, conn=conn)

        # Step 4: Persist all ranked multi-strategy signals into daily_scan_results
        persist_daily_scan_ranking(conn, ranking, scan_run_id=run_id)

        # Step 5: Market Scanner Execution (for legacy scan summary model)
        scanner = MarketScanner()
        summary = scanner.scan_summary(index_name=universe, strategy_name=strategy, db_path=db_path)

        # Step 6: Record COMPLETED status in daily_scan_runs
        completed_at = datetime.now().isoformat()
        actual_scan_date = ranking.signal_date or summary.scan_date or target_date

        cursor.execute(
            """
            UPDATE daily_scan_runs
            SET scan_date = ?,
                status = 'COMPLETED',
                completed_at = ?,
                stocks_processed = ?,
                buy_count = ?,
                watch_count = ?,
                hold_count = ?,
                skipped_count = ?,
                error_count = ?,
                updated_at = datetime('now')
            WHERE id = ?;
            """,
            (
                actual_scan_date,
                completed_at,
                ranking.evaluated_count,
                ranking.buy_signal_count,
                summary.watch_count,
                ranking.evaluated_count - ranking.buy_signal_count,
                ranking.excluded_count,
                0,
                run_id,
            ),
        )
        conn.commit()
        conn.close()

        return summary

    except Exception as exc:
        logger.error(f"Error during daily scan workflow execution: {exc}", exc_info=True)
        if run_id:
            try:
                fail_conn = get_db_connection(db_path)
                fail_cursor = fail_conn.cursor()
                fail_cursor.execute(
                    """
                    UPDATE daily_scan_runs
                    SET status = 'FAILED',
                        error_message = ?,
                        updated_at = datetime('now')
                    WHERE id = ?;
                    """,
                    (str(exc), run_id),
                )
                fail_conn.commit()
                fail_conn.close()
            except Exception as save_err:
                logger.error(f"Failed to save FAILED status: {save_err}")
        raise exc

    finally:
        _SCAN_WORKFLOW_LOCK.release()
