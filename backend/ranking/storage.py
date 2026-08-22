"""
Persistence and query layer for Daily Multi-Strategy Scan Rankings.

Stores immutable daily snapshots into `daily_scan_results` and provides
fast, read-only queries for today's and historical scan recommendations.
"""
import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from backend.aggregator.models import AggregatedSignalStrength
from backend.ranking.models import DailySignalRanking, RankedSignal, SignalTier

logger = logging.getLogger(__name__)


def persist_daily_scan_ranking(
    conn: sqlite3.Connection,
    ranking: DailySignalRanking,
    scan_run_id: Optional[int] = None,
) -> int:
    """
    Persists all evaluated ranked signals from DailySignalRanking into `daily_scan_results`.
    Guarantees atomic insertion inside the transaction.

    Returns the count of persisted signal records.
    """
    if not ranking.results:
        return 0

    if not ranking.signal_date:
        raise ValueError("Cannot persist DailySignalRanking without a valid signal_date.")

    cursor = conn.cursor()

    actual_scan_run_id = scan_run_id
    if scan_run_id is not None:
        cursor.execute("SELECT 1 FROM daily_scan_runs WHERE id = ?;", (scan_run_id,))
        if not cursor.fetchone():
            actual_scan_run_id = None

    # Pre-fetch stock_id mapping for all symbols to avoid per-row queries
    cursor.execute("SELECT id, symbol FROM stocks;")
    symbol_to_id = {row["symbol"]: row["id"] for row in cursor.fetchall()}

    persisted_count = 0
    for sig in ranking.results:
        stock_id = symbol_to_id.get(sig.symbol)
        if not stock_id:
            # Look up or insert stock if missing in test environments
            cursor.execute("SELECT id FROM stocks WHERE symbol = ?;", (sig.symbol,))
            row = cursor.fetchone()
            if row:
                stock_id = row["id"]
            else:
                logger.warning(f"Stock symbol '{sig.symbol}' not found in stocks table. Skipping persistence.")
                continue

        cursor.execute(
            """
            INSERT INTO daily_scan_results (
                scan_run_id,
                scan_date,
                stock_id,
                symbol,
                rank,
                score,
                strength,
                tier,
                buy_count,
                strategies_evaluated,
                strategies_total,
                buy_strategies,
                hold_strategies,
                error_strategies,
                best_strategy_name,
                entry_price,
                stop_loss,
                target_price,
                risk_reward,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(scan_date, stock_id) DO UPDATE SET
                scan_run_id = excluded.scan_run_id,
                rank = excluded.rank,
                score = excluded.score,
                strength = excluded.strength,
                tier = excluded.tier,
                buy_count = excluded.buy_count,
                strategies_evaluated = excluded.strategies_evaluated,
                strategies_total = excluded.strategies_total,
                buy_strategies = excluded.buy_strategies,
                hold_strategies = excluded.hold_strategies,
                error_strategies = excluded.error_strategies,
                best_strategy_name = excluded.best_strategy_name,
                entry_price = excluded.entry_price,
                stop_loss = excluded.stop_loss,
                target_price = excluded.target_price,
                risk_reward = excluded.risk_reward;
            """,
            (
                actual_scan_run_id,
                ranking.signal_date,
                stock_id,
                sig.symbol,
                sig.rank,
                sig.score,
                sig.strength.value if hasattr(sig.strength, "value") else str(sig.strength),
                sig.tier.value if hasattr(sig.tier, "value") else str(sig.tier),
                sig.buy_count,
                sig.strategies_evaluated,
                sig.strategies_total,
                json.dumps(sig.buy_strategies),
                json.dumps(sig.hold_strategies),
                json.dumps(sig.error_strategies),
                sig.best_strategy_name,
                sig.best_entry_price,
                sig.best_stop_loss,
                sig.best_target_price,
                sig.best_risk_reward,
            ),
        )
        persisted_count += 1

    conn.commit()
    logger.info(f"Persisted {persisted_count} ranked signals for date {ranking.signal_date}.")
    return persisted_count


def get_persisted_daily_ranking(
    conn: sqlite3.Connection,
    scan_date: Optional[str] = None,
    limit: Optional[int] = None,
    universe: str = "NIFTY_NEXT_50",
) -> Optional[DailySignalRanking]:
    """
    Fast, read-only query that reconstructs DailySignalRanking from `daily_scan_results`.
    Never recalculates indicators or executes strategies.

    If scan_date is None, loads the latest available scan_date from the table.
    """
    cursor = conn.cursor()

    target_date = scan_date
    if not target_date:
        cursor.execute("SELECT MAX(scan_date) FROM daily_scan_results;")
        row = cursor.fetchone()
        if row and row[0]:
            target_date = str(row[0])
        else:
            return None

    # Query all results for the target date joined with stocks table for company_name
    cursor.execute(
        """
        SELECT 
            r.rank,
            r.symbol,
            s.company_name,
            r.scan_date,
            r.score,
            r.strength,
            r.tier,
            r.buy_count,
            r.strategies_evaluated,
            r.strategies_total,
            r.buy_strategies,
            r.hold_strategies,
            r.error_strategies,
            r.best_strategy_name,
            r.entry_price,
            r.stop_loss,
            r.target_price,
            r.risk_reward
        FROM daily_scan_results r
        LEFT JOIN stocks s ON r.stock_id = s.id
        WHERE r.scan_date = ?
        ORDER BY r.rank ASC;
        """,
        (target_date,),
    )
    rows = cursor.fetchall()

    if not rows:
        return None

    results: List[RankedSignal] = []
    for r in rows:
        buy_strats = json.loads(r["buy_strategies"]) if r["buy_strategies"] else []
        hold_strats = json.loads(r["hold_strategies"]) if r["hold_strategies"] else []
        err_strats = json.loads(r["error_strategies"]) if r["error_strategies"] else []

        results.append(
            RankedSignal(
                rank=r["rank"],
                symbol=r["symbol"],
                company_name=r["company_name"],
                signal_date=r["scan_date"],
                score=r["score"],
                strength=AggregatedSignalStrength(r["strength"]),
                tier=SignalTier(r["tier"]),
                buy_count=r["buy_count"],
                strategies_evaluated=r["strategies_evaluated"],
                strategies_total=r["strategies_total"],
                buy_strategies=buy_strats,
                hold_strategies=hold_strats,
                error_strategies=err_strats,
                best_strategy_name=r["best_strategy_name"],
                best_entry_price=r["entry_price"],
                best_stop_loss=r["stop_loss"],
                best_target_price=r["target_price"],
                best_risk_reward=r["risk_reward"],
            )
        )

    # Calculate summary metadata
    evaluated_count = len(results)
    buy_signal_count = sum(1 for r in results if r.buy_count > 0)
    shortlist = results[:limit] if limit is not None else []

    return DailySignalRanking(
        signal_date=target_date,
        universe=universe,
        universe_size=evaluated_count,
        evaluated_count=evaluated_count,
        excluded_count=0,
        buy_signal_count=buy_signal_count,
        results=results,
        shortlist=shortlist,
    )


def get_historical_scan_summaries(
    conn: sqlite3.Connection,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Returns a list of all historical scan dates, their completion status,
    stocks evaluated, and BUY setup counts, sorted newest first.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            r.scan_date,
            COUNT(r.id) AS stocks_evaluated,
            SUM(CASE WHEN r.buy_count > 0 THEN 1 ELSE 0 END) AS buy_setups,
            SUM(CASE WHEN r.strength IN ('STRONG', 'VERY_STRONG') THEN 1 ELSE 0 END) AS strong_signals,
            MAX(r.created_at) AS completed_at,
            COALESCE(MAX(sr.status), 'COMPLETED') AS status
        FROM daily_scan_results r
        LEFT JOIN daily_scan_runs sr ON r.scan_run_id = sr.id
        GROUP BY r.scan_date
        ORDER BY r.scan_date DESC
        LIMIT ?;
        """,
        (limit,),
    )
    rows = cursor.fetchall()

    summaries: List[Dict[str, Any]] = []
    for row in rows:
        summaries.append({
            "scan_date": row["scan_date"],
            "status": row["status"],
            "stocks_evaluated": row["stocks_evaluated"],
            "buy_setups": row["buy_setups"] or 0,
            "strong_signals": row["strong_signals"] or 0,
            "completed_at": row["completed_at"],
        })

    return summaries
