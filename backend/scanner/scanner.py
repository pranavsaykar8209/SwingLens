import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from backend.database.connection import get_db_connection, DEFAULT_DB_PATH
from backend.indicators.engine import get_price_history, calculate_indicators
from backend.strategies.base import BaseStrategy
from backend.strategies.registry import get_strategy
from .filters import get_active_universe_constituents, validate_candle_data
from .models import ScanResult, ScanSignalType, ScanSummary

logger = logging.getLogger(__name__)


class MarketScanner:
    """
    Daily Market Scanner backend service.

    Evaluates active stock constituents of a given index (e.g. NIFTY_NEXT_50) against a
    trading strategy (e.g. EMA Pullback v1.0) using local completed daily price candles from SQLite.

    STRICT NO-LOOKAHEAD RULE:
    -------------------------
    The scanner strictly evaluates signals using only historical candles at or before `as_of_date`
    (or the latest completed daily candle available). It never downloads external/live market data,
    never mutates daily prices, and never looks into future candles.
    """

    def scan(
        self,
        index_name: str = "NIFTY_NEXT_50",
        strategy_name: Union[str, BaseStrategy] = "ema_pullback",
        strategy_params: Optional[Dict[str, Any]] = None,
        as_of_date: Optional[str] = None,
        min_required_candles: int = 200,
        db_path: Union[str, Path] = DEFAULT_DB_PATH,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[ScanResult]:
        """
        Executes a scan over active index members using the specified strategy.

        Parameters:
        - index_name: Name of the index universe stored in `index_memberships` (e.g. "NIFTY_NEXT_50").
        - strategy_name: Strategy identifier string (registered in registry) or BaseStrategy instance.
        - strategy_params: Optional parameter overrides for the strategy.
        - as_of_date: Optional cutoff date string (YYYY-MM-DD) for completed candles and membership.
        - min_required_candles: Minimum required price history length for warm-up.
        - db_path: Path to SQLite database file.
        - conn: Existing SQLite database connection (optional).

        Returns:
        - List[ScanResult]: Structured scan results for all scanned constituents.
        """
        should_close = False
        if conn is None:
            conn = get_db_connection(db_path)
            should_close = True

        try:
            # 1. Resolve strategy instance
            if isinstance(strategy_name, BaseStrategy):
                strategy = strategy_name
            else:
                strategy = get_strategy(strategy_name, parameters=strategy_params)

            # 2. Retrieve active constituents for universe
            constituents = get_active_universe_constituents(conn, index_name=index_name, as_of_date=as_of_date)

            results: List[ScanResult] = []

            # 3. Evaluate each constituent
            for stock in constituents:
                symbol = stock["symbol"]
                company_name = stock.get("company_name")

                try:
                    # Fetch historical price history from SQLite
                    df = get_price_history(conn, symbol=symbol, end_date=as_of_date)

                    # Validate candle sufficiency and column availability
                    validate_candle_data(
                        df,
                        min_required_candles=min_required_candles,
                        required_cols=["trade_date", "open", "high", "low", "close", "volume"],
                    )

                    # Calculate technical indicators required by strategy
                    df_indicators = calculate_indicators(df, strategy.required_indicators)

                    # Generate latest signal from completed daily candles
                    latest_signal = strategy.generate_latest_signal(df_indicators)

                    if latest_signal is None:
                        raise ValueError("Strategy returned no signal for price history")

                    latest_close = float(df_indicators["close"].iloc[-1])
                    signal_enum = ScanSignalType(latest_signal.signal.value)

                    results.append(
                        ScanResult(
                            symbol=symbol,
                            company_name=company_name,
                            signal=signal_enum,
                            signal_date=latest_signal.signal_date,
                            close=round(latest_close, 2),
                            entry_price=latest_signal.entry_price,
                            stop_loss=latest_signal.stop_loss,
                            target_price=latest_signal.target_price,
                            risk_reward=latest_signal.risk_reward,
                            score=latest_signal.score,
                            strategy_name=strategy.name,
                            strategy_version=strategy.version,
                            reason=latest_signal.reason,
                            metadata=latest_signal.metadata,
                            error=None,
                            status="SUCCESS",
                        )
                    )

                except Exception as e:
                    logger.warning(f"Error scanning symbol '{symbol}': {e}")
                    results.append(
                        ScanResult(
                            symbol=symbol,
                            company_name=company_name,
                            signal=ScanSignalType.ERROR,
                            signal_date=as_of_date,
                            close=None,
                            entry_price=None,
                            stop_loss=None,
                            target_price=None,
                            risk_reward=None,
                            score=None,
                            strategy_name=strategy.name,
                            strategy_version=strategy.version,
                            reason=None,
                            metadata={},
                            error=str(e),
                            status="ERROR",
                        )
                    )

            return results

        finally:
            if should_close and conn:
                conn.close()

    def scan_summary(
        self,
        index_name: str = "NIFTY_NEXT_50",
        strategy_name: Union[str, BaseStrategy] = "ema_pullback",
        strategy_params: Optional[Dict[str, Any]] = None,
        as_of_date: Optional[str] = None,
        min_required_candles: int = 200,
        db_path: Union[str, Path] = DEFAULT_DB_PATH,
        conn: Optional[sqlite3.Connection] = None,
    ) -> ScanSummary:
        """
        Executes a scan and returns a structured ScanSummary object.
        """
        results = self.scan(
            index_name=index_name,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            as_of_date=as_of_date,
            min_required_candles=min_required_candles,
            db_path=db_path,
            conn=conn,
        )

        valid_dates = [r.signal_date for r in results if r.signal_date and r.status == "SUCCESS"]
        latest_date = max(valid_dates) if valid_dates else (as_of_date or "")

        buy_count = sum(1 for r in results if r.signal == ScanSignalType.BUY)
        watch_count = sum(1 for r in results if r.signal == ScanSignalType.WATCH)
        hold_count = sum(1 for r in results if r.signal == ScanSignalType.HOLD)
        error_count = sum(1 for r in results if r.signal == ScanSignalType.ERROR)

        if isinstance(strategy_name, BaseStrategy):
            strat_name = strategy_name.name
            strat_ver = strategy_name.version
        else:
            strat_obj = get_strategy(strategy_name)
            strat_name = strat_obj.name
            strat_ver = strat_obj.version

        return ScanSummary(
            scan_date=latest_date,
            universe=index_name,
            strategy=strat_name,
            strategy_version=strat_ver,
            scanned_count=len(results),
            buy_count=buy_count,
            watch_count=watch_count,
            hold_count=hold_count,
            error_count=error_count,
            results=results,
        )
