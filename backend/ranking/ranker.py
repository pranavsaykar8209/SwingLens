"""
DailySignalRanker — Daily Signal Ranking layer for SwingLens.

Workflow:
  1. Fetch active NIFTY Next 50 constituents from SQLite (dynamic, never hardcoded).
  2. For each constituent, run SignalAggregator.aggregate() using the existing
     price history.
  3. Rank results by: score DESC → buy_count DESC → best_risk_reward DESC → symbol ASC.
  4. Return a DailySignalRanking with full results and an optional top-N shortlist.

Design constraints:
  - Does NOT duplicate scanner logic. Reuses SignalAggregator and get_price_history.
  - Does NOT hardcode any stock symbols.
  - Does NOT add weights, ML, or probability estimates.
  - One stock failing does NOT abort the entire run.
  - A single DB connection is opened per run and shared across all stock fetches
    to avoid O(N) connection overhead.
"""
import logging
from pathlib import Path
from typing import List, Optional, Union
import sqlite3

from backend.database.connection import get_db_connection, DEFAULT_DB_PATH
from backend.indicators.engine import get_price_history
from backend.scanner.filters import get_active_universe_constituents
from backend.aggregator.aggregator import SignalAggregator, PRODUCTION_STRATEGY_KEYS
from backend.aggregator.models import AggregatedSignalResult
from .models import DailySignalRanking, RankedSignal, SignalTier, strength_to_tier

logger = logging.getLogger(__name__)

# Minimum candles required for warm-up (same threshold as MarketScanner)
MIN_REQUIRED_CANDLES = 200


def _rank_key(result: AggregatedSignalResult):
    """
    Sort key for ranking aggregated results.

    Priority (descending):
      1. score           — raw BUY count (higher is better)
      2. buy_count       — tie-break on same score
      3. best_risk_reward — tie-break on same score & buy_count (higher is better)
      4. symbol          — final deterministic alphabetical tie-breaker (lower is better)
    """
    rr = result.best_risk_reward if result.best_risk_reward is not None else 0.0
    return (-result.score, -result.buy_count, -rr, result.symbol)


class DailySignalRanker:
    """
    Runs the full daily signal ranking pipeline:
      active universe → per-stock aggregation → ranked output.
    """

    def run(
        self,
        index_name: str = "NIFTY_NEXT_50",
        as_of_date: Optional[str] = None,
        limit: Optional[int] = None,
        strategy_keys: Optional[List[str]] = None,
        min_required_candles: int = MIN_REQUIRED_CANDLES,
        db_path: Union[str, Path] = DEFAULT_DB_PATH,
        conn: Optional[sqlite3.Connection] = None,
    ) -> DailySignalRanking:
        """
        Executes the daily ranking pipeline.

        Parameters:
        - index_name: Active index universe name in SQLite (e.g. "NIFTY_NEXT_50").
        - as_of_date: Optional YYYY-MM-DD cutoff (uses latest candle if None).
        - limit: Optional top-N shortlist size. None returns an empty shortlist.
        - strategy_keys: Optional subset of strategy keys. Defaults to all 5.
        - min_required_candles: Minimum history required for warm-up.
        - db_path: SQLite database path.
        - conn: Existing connection (optional; will be reused across all stocks).

        Returns:
        - DailySignalRanking with ranked results and optional shortlist.
        """
        if strategy_keys is None:
            strategy_keys = list(PRODUCTION_STRATEGY_KEYS)

        should_close = False
        if conn is None:
            conn = get_db_connection(db_path)
            should_close = True

        try:
            # 1. Fetch active universe constituents (dynamic — no hardcoded symbols)
            constituents = get_active_universe_constituents(
                conn, index_name=index_name, as_of_date=as_of_date
            )
            universe_size = len(constituents)

            aggregator = SignalAggregator()
            ranked_inputs: List[tuple] = []  # (AggregatedSignalResult, company_name)
            excluded_count = 0
            signal_date: Optional[str] = None

            # 2. Evaluate each constituent through the aggregator
            for stock in constituents:
                symbol = stock["symbol"]
                company_name = stock.get("company_name")

                try:
                    df = get_price_history(conn, symbol=symbol, end_date=as_of_date)

                    if df is None or df.empty:
                        logger.warning(f"No price history for '{symbol}'. Skipping.")
                        excluded_count += 1
                        continue

                    if len(df) < min_required_candles:
                        logger.warning(
                            f"Insufficient history for '{symbol}': "
                            f"{len(df)} candles < {min_required_candles} required. Skipping."
                        )
                        excluded_count += 1
                        continue

                    result = aggregator.aggregate(
                        symbol=symbol, df=df, strategy_keys=strategy_keys
                    )
                    ranked_inputs.append((result, company_name))

                    # Track the most recent signal date across all stocks
                    if result.signal_date:
                        if signal_date is None or result.signal_date > signal_date:
                            signal_date = result.signal_date

                except Exception as exc:
                    logger.warning(f"Unexpected error for '{symbol}': {exc}", exc_info=False)
                    excluded_count += 1

            # 3. Rank by: score DESC → buy_count DESC → RR DESC → symbol ASC
            ranked_inputs.sort(key=lambda x: _rank_key(x[0]))

            # 4. Build RankedSignal list with rank positions
            results: List[RankedSignal] = []
            for rank_pos, (agg_result, company_name) in enumerate(ranked_inputs, start=1):
                results.append(
                    RankedSignal(
                        rank=rank_pos,
                        symbol=agg_result.symbol,
                        company_name=company_name,
                        signal_date=agg_result.signal_date,
                        score=agg_result.score,
                        strength=agg_result.strength,
                        tier=strength_to_tier(agg_result.strength),
                        buy_count=agg_result.buy_count,
                        strategies_evaluated=agg_result.strategies_evaluated,
                        strategies_total=agg_result.strategies_total,
                        buy_strategies=agg_result.buy_strategies,
                        hold_strategies=agg_result.hold_strategies,
                        error_strategies=agg_result.error_strategies,
                        best_strategy_name=agg_result.best_strategy_name,
                        best_entry_price=agg_result.best_entry_price,
                        best_stop_loss=agg_result.best_stop_loss,
                        best_target_price=agg_result.best_target_price,
                        best_risk_reward=agg_result.best_risk_reward,
                    )
                )

            buy_signal_count = sum(1 for r in results if r.buy_count > 0)
            shortlist = results[:limit] if limit is not None else []

            return DailySignalRanking(
                signal_date=signal_date,
                universe=index_name,
                universe_size=universe_size,
                evaluated_count=len(results),
                excluded_count=excluded_count,
                buy_signal_count=buy_signal_count,
                results=results,
                shortlist=shortlist,
            )

        finally:
            if should_close and conn:
                conn.close()
