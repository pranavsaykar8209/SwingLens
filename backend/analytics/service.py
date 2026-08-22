"""
Strategy Historical Quality Analytics Service.

Evaluates historical quality metrics for trading strategies across representative
or configured stock samples using event-driven backtesting and candle-by-candle
outcome evaluation without lookahead bias.
"""
import logging
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd

from backend.backtest.engine import BacktestEngine
from backend.backtest.models import BacktestResult, ExitReason, Trade
from backend.database.connection import DEFAULT_DB_PATH, get_db_connection
from backend.indicators.engine import get_price_history
from backend.research.validator import DEFAULT_REPRESENTATIVE_SAMPLE
from backend.strategies.base import BaseStrategy
from backend.strategies.registry import _GLOBAL_REGISTRY, get_strategy, list_strategies
from .models import (
    StrategyAnalyticsResponse,
    StrategyQualityClassification,
    StrategyQualityMetrics,
    StrategyStockMetrics,
)

logger = logging.getLogger(__name__)

# Minimum trade sample size required for meaningful statistical classification
MIN_TRADES_FOR_CLASSIFICATION = 10


def classify_strategy(
    trades: int,
    total_r: float,
    profit_factor: float,
    average_r: float,
    min_trades: int = MIN_TRADES_FOR_CLASSIFICATION,
) -> Tuple[StrategyQualityClassification, str]:
    """
    Deterministic rule-based strategy classification.

    Rules:
    1. INSUFFICIENT_DATA: trades < min_trades
    2. POSITIVE: trades >= min_trades and total_r > 0.0 and profit_factor >= 1.0 and average_r > 0.0
    3. NEGATIVE: trades >= min_trades and total_r < 0.0 and profit_factor < 1.0 and average_r < 0.0
    4. NEUTRAL: trades >= min_trades and does not satisfy all positive or all negative conditions
    """
    if trades < min_trades:
        return (
            StrategyQualityClassification.INSUFFICIENT_DATA,
            f"Insufficient sample size: {trades} trades (< {min_trades} required for statistical evaluation).",
        )

    if total_r > 0.0 and profit_factor >= 1.0 and average_r > 0.0:
        return (
            StrategyQualityClassification.POSITIVE,
            f"Positive historical performance: total_r={total_r:.2f} > 0, profit_factor={profit_factor:.2f} >= 1.0, average_r={average_r:.2f} > 0.",
        )

    if total_r < 0.0 and profit_factor < 1.0 and average_r < 0.0:
        return (
            StrategyQualityClassification.NEGATIVE,
            f"Negative historical performance: total_r={total_r:.2f} < 0, profit_factor={profit_factor:.2f} < 1.0, average_r={average_r:.2f} < 0.",
        )

    return (
        StrategyQualityClassification.NEUTRAL,
        f"Neutral / mixed historical performance: total_r={total_r:.2f}, profit_factor={profit_factor:.2f}, average_r={average_r:.2f}.",
    )


class StrategyAnalyticsService:
    """
    Service responsible for computing strategy quality metrics and classifications.
    """

    def __init__(self, db_path: Union[str, Path] = DEFAULT_DB_PATH):
        self.db_path = db_path

    def _load_stock_data(
        self,
        conn: sqlite3.Connection,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_candles: int = 100,
    ) -> Dict[str, pd.DataFrame]:
        """
        Loads historical daily price DataFrames for given symbols within date bounds.
        """
        stock_data: Dict[str, pd.DataFrame] = {}
        for sym in symbols:
            clean_sym = sym.strip().upper()
            df = get_price_history(conn, clean_sym, start_date=start_date, end_date=end_date)
            if df.empty or len(df) < min_candles:
                logger.debug(f"Skipping symbol '{clean_sym}' (insufficient data: {len(df)} candles).")
                continue
            df["symbol"] = clean_sym
            stock_data[clean_sym] = df
        return stock_data

    def _analyze_trade_excursions(
        self, trade: Trade, df: pd.DataFrame
    ) -> Tuple[Optional[float], Optional[float], bool]:
        """
        Calculates Maximum Favorable Excursion (MFE in R), Maximum Adverse Excursion (MAE in R),
        and whether an ambiguous same-candle target & stop touch occurred during the trade holding window.
        """
        mask = (df["trade_date"] >= trade.entry_date) & (df["trade_date"] <= trade.exit_date)
        candles = df.loc[mask]
        if candles.empty:
            return None, None, False

        risk = abs(trade.entry_price - trade.stop_loss) if trade.stop_loss is not None else None
        valid_risk = risk is not None and risk > 1e-4

        max_high = float(candles["high"].max())
        min_low = float(candles["low"].min())
        mfe_points = max(0.0, max_high - trade.entry_price)
        mae_points = max(0.0, trade.entry_price - min_low)

        mfe_r = round(mfe_points / risk, 2) if valid_risk else None
        mae_r = round(mae_points / risk, 2) if valid_risk else None

        is_ambiguous = False
        if trade.target_price is not None and trade.stop_loss is not None:
            is_ambiguous = bool(
                ((candles["high"] >= trade.target_price) & (candles["low"] <= trade.stop_loss)).any()
            )

        return mfe_r, mae_r, is_ambiguous

    def evaluate_strategy_on_data(
        self,
        strategy: BaseStrategy,
        stock_data: Dict[str, pd.DataFrame],
        include_per_stock: bool = True,
    ) -> StrategyQualityMetrics:
        """
        Evaluates a single strategy instance against pre-loaded stock DataFrames.
        """
        engine = BacktestEngine(strategy=strategy)
        per_stock_metrics: Dict[str, StrategyStockMetrics] = {}

        all_trades: List[Trade] = []
        all_r_multiples: List[float] = []
        all_mfe_r: List[float] = []
        all_mae_r: List[float] = []

        total_gross_profit = 0.0
        total_gross_loss = 0.0
        total_holding_days = 0
        total_target_exits = 0
        total_stop_exits = 0
        total_ambiguous_trades = 0
        max_dd_overall = 0.0

        for sym, df in stock_data.items():
            res: BacktestResult = engine.run(df)
            max_dd_overall = max(max_dd_overall, abs(res.max_drawdown_percent))

            stock_trades = res.trades
            stock_wins = sum(1 for t in stock_trades if t.net_pnl > 0)
            stock_losses = sum(1 for t in stock_trades if t.net_pnl <= 0)
            stock_total_trades = len(stock_trades)

            stock_r_list: List[float] = []
            stock_mfe_r_list: List[float] = []
            stock_mae_r_list: List[float] = []
            stock_target_exits = 0
            stock_stop_exits = 0
            stock_ambiguous_count = 0
            stock_gross_profit = 0.0
            stock_gross_loss = 0.0
            stock_holding_days = 0

            for t in stock_trades:
                all_trades.append(t)
                stock_holding_days += t.holding_days
                total_holding_days += t.holding_days

                if t.net_pnl > 0:
                    stock_gross_profit += t.net_pnl
                    total_gross_profit += t.net_pnl
                else:
                    stock_gross_loss += abs(t.net_pnl)
                    total_gross_loss += abs(t.net_pnl)

                if t.r_multiple is not None:
                    stock_r_list.append(t.r_multiple)
                    all_r_multiples.append(t.r_multiple)

                if t.exit_reason == ExitReason.TARGET.value:
                    stock_target_exits += 1
                    total_target_exits += 1
                elif t.exit_reason == ExitReason.STOP_LOSS.value:
                    stock_stop_exits += 1
                    total_stop_exits += 1

                mfe_r, mae_r, is_ambiguous = self._analyze_trade_excursions(t, df)
                if mfe_r is not None:
                    stock_mfe_r_list.append(mfe_r)
                    all_mfe_r.append(mfe_r)
                if mae_r is not None:
                    stock_mae_r_list.append(mae_r)
                    all_mae_r.append(mae_r)
                if is_ambiguous:
                    stock_ambiguous_count += 1
                    total_ambiguous_trades += 1

            stock_win_rate = round(stock_wins / stock_total_trades * 100.0, 2) if stock_total_trades > 0 else 0.0
            stock_avg_r = round(sum(stock_r_list) / len(stock_r_list), 2) if stock_r_list else 0.0
            stock_total_r = round(sum(stock_r_list), 2) if stock_r_list else 0.0
            stock_profit_factor = (
                round(stock_gross_profit / stock_gross_loss, 2)
                if stock_gross_loss > 0
                else (99.99 if stock_gross_profit > 0 else 0.0)
            )
            stock_avg_holding = round(stock_holding_days / stock_total_trades, 1) if stock_total_trades > 0 else 0.0
            stock_target_rate = round(stock_target_exits / stock_total_trades * 100.0, 2) if stock_total_trades > 0 else 0.0
            stock_stop_rate = round(stock_stop_exits / stock_total_trades * 100.0, 2) if stock_total_trades > 0 else 0.0
            stock_ambiguous_rate = round(stock_ambiguous_count / stock_total_trades * 100.0, 2) if stock_total_trades > 0 else 0.0
            stock_avg_mfe = round(sum(stock_mfe_r_list) / len(stock_mfe_r_list), 2) if stock_mfe_r_list else 0.0
            stock_avg_mae = round(sum(stock_mae_r_list) / len(stock_mae_r_list), 2) if stock_mae_r_list else 0.0

            per_stock_metrics[sym] = StrategyStockMetrics(
                symbol=sym,
                trades=stock_total_trades,
                wins=stock_wins,
                losses=stock_losses,
                win_rate=stock_win_rate,
                average_r=stock_avg_r,
                total_r=stock_total_r,
                profit_factor=stock_profit_factor,
                max_drawdown=round(abs(res.max_drawdown_percent), 2),
                average_holding_days=stock_avg_holding,
                target_hit_rate=stock_target_rate,
                stop_hit_rate=stock_stop_rate,
                ambiguous_rate=stock_ambiguous_rate,
                average_mfe_r=stock_avg_mfe,
                average_mae_r=stock_avg_mae,
            )

        total_trades = len(all_trades)
        wins = sum(1 for t in all_trades if t.net_pnl > 0)
        losses = sum(1 for t in all_trades if t.net_pnl <= 0)
        win_rate = round(wins / total_trades * 100.0, 2) if total_trades > 0 else 0.0
        average_r = round(sum(all_r_multiples) / len(all_r_multiples), 2) if all_r_multiples else 0.0
        total_r = round(sum(all_r_multiples), 2) if all_r_multiples else 0.0
        profit_factor = (
            round(total_gross_profit / total_gross_loss, 2)
            if total_gross_loss > 0
            else (99.99 if total_gross_profit > 0 else 0.0)
        )
        avg_holding_days = round(total_holding_days / total_trades, 1) if total_trades > 0 else 0.0
        target_hit_rate = round(total_target_exits / total_trades * 100.0, 2) if total_trades > 0 else 0.0
        stop_hit_rate = round(total_stop_exits / total_trades * 100.0, 2) if total_trades > 0 else 0.0
        ambiguous_rate = round(total_ambiguous_trades / total_trades * 100.0, 2) if total_trades > 0 else 0.0
        average_mfe_r = round(sum(all_mfe_r) / len(all_mfe_r), 2) if all_mfe_r else 0.0
        average_mae_r = round(sum(all_mae_r) / len(all_mae_r), 2) if all_mae_r else 0.0

        classification, reason = classify_strategy(
            trades=total_trades,
            total_r=total_r,
            profit_factor=profit_factor,
            average_r=average_r,
        )

        return StrategyQualityMetrics(
            strategy_name=strategy.name,
            strategy_version=strategy.version,
            classification=classification,
            classification_reason=reason,
            trades=total_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            average_r=average_r,
            total_r=total_r,
            profit_factor=profit_factor,
            max_drawdown=round(max_dd_overall, 2),
            average_holding_days=avg_holding_days,
            target_hit_rate=target_hit_rate,
            stop_hit_rate=stop_hit_rate,
            ambiguous_rate=ambiguous_rate,
            average_mfe_r=average_mfe_r,
            average_mae_r=average_mae_r,
            stocks_tested=len(stock_data),
            per_stock=per_stock_metrics if include_per_stock else None,
        )

    def get_strategy_quality(
        self,
        strategy_name: str,
        symbols: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> StrategyQualityMetrics:
        """
        Computes quality analytics for a single registered strategy by name.
        """
        strategy = get_strategy(strategy_name)
        target_symbols = symbols or list(DEFAULT_REPRESENTATIVE_SAMPLE)

        should_close = False
        if conn is None:
            conn = get_db_connection(self.db_path)
            should_close = True

        try:
            stock_data = self._load_stock_data(
                conn, target_symbols, start_date=start_date, end_date=end_date
            )
            return self.evaluate_strategy_on_data(strategy, stock_data, include_per_stock=True)
        finally:
            if should_close:
                conn.close()

    def get_all_strategies_quality(
        self,
        symbols: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> StrategyAnalyticsResponse:
        """
        Computes quality analytics across all registered strategies in the registry.
        """
        target_symbols = symbols or list(DEFAULT_REPRESENTATIVE_SAMPLE)

        should_close = False
        if conn is None:
            conn = get_db_connection(self.db_path)
            should_close = True

        try:
            stock_data = self._load_stock_data(
                conn, target_symbols, start_date=start_date, end_date=end_date
            )

            registered_metas = list_strategies()
            strategy_results: List[StrategyQualityMetrics] = []

            for meta in registered_metas:
                name = meta["name"]
                try:
                    strategy = get_strategy(name)
                    metrics = self.evaluate_strategy_on_data(
                        strategy, stock_data, include_per_stock=False
                    )
                    strategy_results.append(metrics)
                except Exception as exc:
                    logger.warning(f"Error evaluating strategy '{name}': {exc}")

            return StrategyAnalyticsResponse(
                start_date=start_date,
                end_date=end_date,
                symbols=list(stock_data.keys()),
                strategies=strategy_results,
            )
        finally:
            if should_close:
                conn.close()
