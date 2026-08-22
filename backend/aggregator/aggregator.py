"""
SignalAggregator — Multi-Strategy Signal Aggregator for SwingLens.

Design rules:
  - Reads the existing global strategy registry (_GLOBAL_REGISTRY).
    Does NOT create a second registry.
  - Never modifies any individual strategy's logic or output.
  - Applies a simple transparent scoring rule: BUY=1, everything else=0.
  - Strategies that raise exceptions are excluded from both score and
    denominator; 'strategies_evaluated' reflects only clean evaluations.
  - No weights, no ML, no probability estimates.
"""
import logging
from pathlib import Path
from typing import List, Optional, Union
import sqlite3

import pandas as pd

from backend.database.connection import get_db_connection, DEFAULT_DB_PATH
from backend.indicators.engine import get_price_history, calculate_indicators
from backend.strategies.models import SignalType
from backend.strategies.registry import _GLOBAL_REGISTRY
from .models import (
    AggregatedSignalResult,
    AggregatedSignalStrength,
    StrategyVote,
    score_to_strength,
)

logger = logging.getLogger(__name__)


# Strategy registry keys for the 5 frozen production strategies.
# Maintained here explicitly so that test/example strategies registered in
# the global registry (e.g. PassthroughHoldStrategy) are never included in
# aggregated results unless the caller explicitly opts them in.
PRODUCTION_STRATEGY_KEYS = [
    "ema_pullback",
    "ma_trend_breakout",
    "rsi_mean_reversion",
    "macd_momentum",
    "bollinger_squeeze",
]


class SignalAggregator:
    """
    Runs all 5 production strategies against a single stock independently
    and combines their latest signals into a transparent scored result.

    Usage:
        aggregator = SignalAggregator()
        result = aggregator.aggregate_for_symbol("BANKBARODA")
    """

    def aggregate(
        self,
        symbol: str,
        df: pd.DataFrame,
        strategy_keys: Optional[List[str]] = None,
    ) -> AggregatedSignalResult:
        """
        Runs each strategy against the supplied price DataFrame and produces
        a combined AggregatedSignalResult.

        Parameters:
        - symbol: Stock ticker (used only for labelling the result).
        - df: Price DataFrame with OHLCV columns, sorted chronologically.
              Must already contain a 'symbol' column or it will be added.
        - strategy_keys: Optional list of registry key strings to evaluate.
                         Defaults to PRODUCTION_STRATEGY_KEYS (all 5 strategies).

        Returns:
        - AggregatedSignalResult with score, strength, and per-strategy votes.
        """
        if strategy_keys is None:
            strategy_keys = list(PRODUCTION_STRATEGY_KEYS)

        # Ensure 'symbol' column is present for strategies that expect it
        if "symbol" not in df.columns:
            df = df.copy()
            df["symbol"] = symbol

        votes: List[StrategyVote] = []
        buy_strategies: List[str] = []
        hold_strategies: List[str] = []
        error_strategies: List[str] = []
        signal_date: Optional[str] = None
        best_vote: Optional[StrategyVote] = None

        for key in strategy_keys:
            # Resolve strategy from global registry
            try:
                strategy = _GLOBAL_REGISTRY.get_strategy(key)
            except KeyError:
                logger.warning(f"Strategy key '{key}' not found in registry. Skipping.")
                error_strategies.append(key)
                votes.append(
                    StrategyVote(
                        strategy_name=key,
                        strategy_version="N/A",
                        signal="ERROR",
                        error=f"Strategy key '{key}' not registered.",
                    )
                )
                continue

            # Compute required indicators for this strategy
            try:
                df_ind = calculate_indicators(df, strategy.required_indicators)
                sig = strategy.generate_latest_signal(df_ind)
            except Exception as exc:
                logger.warning(
                    f"Strategy '{strategy.name}' raised an error for '{symbol}': {exc}"
                )
                error_strategies.append(strategy.name)
                votes.append(
                    StrategyVote(
                        strategy_name=strategy.name,
                        strategy_version=strategy.version,
                        signal="ERROR",
                        error=str(exc),
                    )
                )
                continue

            if sig is None:
                # Strategy returned nothing (insufficient data)
                logger.warning(
                    f"Strategy '{strategy.name}' returned no signal for '{symbol}'. Skipping."
                )
                error_strategies.append(strategy.name)
                votes.append(
                    StrategyVote(
                        strategy_name=strategy.name,
                        strategy_version=strategy.version,
                        signal="ERROR",
                        error="Strategy returned no signal (likely insufficient data).",
                    )
                )
                continue

            # Record the latest signal date (prefer the most recent non-None value)
            if sig.signal_date:
                if signal_date is None or sig.signal_date > signal_date:
                    signal_date = sig.signal_date

            vote = StrategyVote(
                strategy_name=strategy.name,
                strategy_version=strategy.version,
                signal=sig.signal.value,
                entry_price=sig.entry_price,
                stop_loss=sig.stop_loss,
                target_price=sig.target_price,
                risk_reward=sig.risk_reward,
                reason=sig.reason,
            )
            votes.append(vote)

            if sig.signal == SignalType.BUY:
                buy_strategies.append(strategy.name)
                # Use the first BUY vote (by strategy_keys order) for best_* fields
                if best_vote is None:
                    best_vote = vote
            else:
                hold_strategies.append(strategy.name)

        # Scoring
        strategies_evaluated = len(strategy_keys) - len(error_strategies)
        score = len(buy_strategies)
        strength = score_to_strength(score)

        return AggregatedSignalResult(
            symbol=symbol,
            signal_date=signal_date,
            strategies_evaluated=strategies_evaluated,
            strategies_total=len(strategy_keys),
            buy_count=len(buy_strategies),
            hold_count=len(hold_strategies),
            score=score,
            strength=strength,
            buy_strategies=buy_strategies,
            hold_strategies=hold_strategies,
            error_strategies=error_strategies,
            best_entry_price=best_vote.entry_price if best_vote else None,
            best_stop_loss=best_vote.stop_loss if best_vote else None,
            best_target_price=best_vote.target_price if best_vote else None,
            best_risk_reward=best_vote.risk_reward if best_vote else None,
            best_strategy_name=best_vote.strategy_name if best_vote else None,
            votes=votes,
        )

    def aggregate_for_symbol(
        self,
        symbol: str,
        as_of_date: Optional[str] = None,
        strategy_keys: Optional[List[str]] = None,
        min_required_candles: int = 200,
        db_path: Union[str, Path] = DEFAULT_DB_PATH,
        conn: Optional[sqlite3.Connection] = None,
    ) -> AggregatedSignalResult:
        """
        Convenience method that fetches price history from SQLite and
        runs aggregate() for the given symbol.

        Parameters:
        - symbol: Stock ticker symbol (e.g. 'BANKBARODA').
        - as_of_date: Optional YYYY-MM-DD cutoff (uses latest candle if None).
        - strategy_keys: Optional subset of strategies. Defaults to all 5.
        - min_required_candles: Minimum candles required for warm-up.
        - db_path: Path to the SQLite database.
        - conn: Existing SQLite connection (optional).

        Raises:
        - ValueError if the symbol has no price history or fewer than
          min_required_candles candles available.
        """
        should_close = False
        if conn is None:
            conn = get_db_connection(db_path)
            should_close = True

        try:
            df = get_price_history(conn, symbol=symbol, end_date=as_of_date)
        finally:
            if should_close:
                conn.close()

        if df is None or df.empty:
            raise ValueError(
                f"No price history found for symbol '{symbol}' in the database."
            )

        if len(df) < min_required_candles:
            raise ValueError(
                f"Insufficient price history for '{symbol}': "
                f"{len(df)} candles available, minimum {min_required_candles} required."
            )

        return self.aggregate(symbol=symbol, df=df, strategy_keys=strategy_keys)
