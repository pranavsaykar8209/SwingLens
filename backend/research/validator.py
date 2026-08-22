import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd
from pydantic import BaseModel, Field

from backend.backtest.engine import BacktestEngine
from backend.backtest.models import BacktestResult
from backend.database.connection import get_db_connection, DEFAULT_DB_PATH
from backend.indicators.engine import get_price_history, calculate_indicators
from backend.scanner.filters import get_active_universe_constituents
from backend.strategies.base import BaseStrategy
from backend.strategies.models import SignalType
from backend.strategies.registry import get_strategy, list_strategies

logger = logging.getLogger(__name__)

# Default representative stock sample (10 stocks across key sectors)
DEFAULT_REPRESENTATIVE_SAMPLE = [
    "BANKBARODA",  # Banking / PSU Financial
    "CHOLAFIN",    # NBFC / Financial Services
    "DIVISLAB",    # Pharma / Healthcare
    "BRITANNIA",   # FMCG / Consumer Goods
    "TVSMOTOR",    # Automotive
    "ABB",         # Industrial / Capital Goods
    "TATAPOWER",   # Energy / Power / Utilities
    "VEDL",        # Metals / Mining
    "DLF",         # Real Estate / Infrastructure
    "LTM",         # IT / Technology
]


class ValidationConfig(BaseModel):
    """Configuration settings for representative strategy validation."""
    symbols: List[str] = Field(default_factory=lambda: list(DEFAULT_REPRESENTATIVE_SAMPLE))
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    strategies: Optional[List[str]] = Field(
        default_factory=lambda: [
            "ema_pullback",
            "ma_trend_breakout",
            "rsi_mean_reversion",
            "macd_momentum",
            "bollinger_squeeze",
        ]
    )
    index_name: str = "NIFTY_NEXT_50"
    min_candles: int = 100
    db_path: Path = DEFAULT_DB_PATH


class AggregatedStrategyMetric(BaseModel):
    """Summary metric aggregation for a single strategy across tested stocks."""
    strategy_name: str
    strategy_version: str
    stocks_tested: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0
    average_r: float = 0.0
    total_r: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_holding_days: float = 0.0
    per_stock_results: Dict[str, BacktestResult] = Field(default_factory=dict)


class SignalOverlapResult(BaseModel):
    """Analysis of signal agreement and uniqueness across strategies."""
    total_buy_signals: int = 0
    strategy_buy_counts: Dict[str, int] = Field(default_factory=dict)
    unique_signal_counts: Dict[str, int] = Field(default_factory=dict)
    agreement_counts: Dict[int, int] = Field(default_factory=dict)  # k -> number of dates where k strategies agreed
    multi_agree_dates: List[Dict[str, Any]] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Complete structured validation report containing metrics, breakdown, and text tables."""
    config: ValidationConfig
    strategy_metrics: List[AggregatedStrategyMetric]
    overlap_result: Optional[SignalOverlapResult] = None
    summary_table_md: str = ""
    per_stock_table_md: str = ""
    overlap_table_md: str = ""


class StrategyValidator:
    """
    Lightweight validation framework executing strategies against representative stock sample.
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()

    def run(self, conn: Optional[sqlite3.Connection] = None) -> ValidationReport:
        """
        Executes strategy validation over configured representative stock sample.
        """
        should_close = False
        if conn is None:
            conn = get_db_connection(self.config.db_path)
            should_close = True

        try:
            # 1. Resolve strategy objects to evaluate
            strategy_names = self.config.strategies
            if not strategy_names:
                strategy_names = [s["name"] for s in list_strategies()]

            strategies: List[BaseStrategy] = []
            for name in strategy_names:
                try:
                    strategies.append(get_strategy(name))
                except KeyError:
                    logger.warning(f"Strategy '{name}' not found in registry. Skipping.")

            if not strategies:
                raise ValueError("No valid registered strategies found for validation.")

            # 2. Fetch stock data for sample symbols
            sample_symbols = [s.strip().upper() for s in self.config.symbols]

            # Fetch active constituents to verify DB presence
            constituents = get_active_universe_constituents(conn, index_name=self.config.index_name)
            valid_symbols = {c["symbol"] for c in constituents}

            stock_data_map: Dict[str, pd.DataFrame] = {}
            for sym in sample_symbols:
                if valid_symbols and sym not in valid_symbols:
                    logger.warning(f"Symbol '{sym}' is not in active '{self.config.index_name}' universe.")

                df = get_price_history(
                    conn,
                    symbol=sym,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                )
                if df.empty:
                    logger.warning(f"No price history found for '{sym}'. Skipping.")
                    continue
                if len(df) < self.config.min_candles:
                    logger.warning(f"Symbol '{sym}' has only {len(df)} candles (< {self.config.min_candles}). Skipping.")
                    continue

                df["symbol"] = sym
                stock_data_map[sym] = df

            if not stock_data_map:
                raise ValueError("No valid price data available for configured symbols.")

            # 3. Execute backtest for each strategy over stock sample
            strategy_metrics: List[AggregatedStrategyMetric] = []
            daily_signals_matrix: Dict[Tuple[str, str], Dict[str, SignalType]] = {}

            for strat in strategies:
                print(f"Evaluating strategy: {strat.name} (v{strat.version})...", flush=True)
                per_stock_results: Dict[str, BacktestResult] = {}
                engine = BacktestEngine(strategy=strat)

                total_trades = 0
                winning_trades = 0
                losing_trades = 0
                total_r = 0.0
                sum_r_multiples = 0.0
                r_multiple_count = 0
                total_gross_profit = 0.0
                total_gross_loss = 0.0
                holding_days_sum = 0.0
                closed_trades_count = 0
                max_dd_overall = 0.0

                for sym, df in stock_data_map.items():
                    res = engine.run(df)
                    per_stock_results[sym] = res

                    total_trades += res.total_trades
                    winning_trades += res.winning_trades
                    losing_trades += res.losing_trades
                    total_r += res.total_r
                    max_dd_overall = max(max_dd_overall, abs(res.max_drawdown_percent))

                    for t in res.trades:
                        if t.r_multiple is not None:
                            sum_r_multiples += t.r_multiple
                            r_multiple_count += 1
                        if t.status == "CLOSED":
                            closed_trades_count += 1
                            holding_days_sum += t.holding_days
                            if t.net_pnl > 0:
                                total_gross_profit += t.net_pnl
                            else:
                                total_gross_loss += abs(t.net_pnl)

                        if t.signal_date:
                            daily_signals_matrix[(sym, t.signal_date)] = daily_signals_matrix.get(
                                (sym, t.signal_date), {}
                            )
                            daily_signals_matrix[(sym, t.signal_date)][strat.name] = SignalType.BUY

                win_rate_pct = round((winning_trades / total_trades * 100.0), 2) if total_trades > 0 else 0.0
                avg_r = round((sum_r_multiples / r_multiple_count), 2) if r_multiple_count > 0 else 0.0
                profit_factor = (
                    round((total_gross_profit / total_gross_loss), 2)
                    if total_gross_loss > 0
                    else (99.99 if total_gross_profit > 0 else 0.0)
                )
                avg_holding = round((holding_days_sum / closed_trades_count), 1) if closed_trades_count > 0 else 0.0

                metric = AggregatedStrategyMetric(
                    strategy_name=strat.name,
                    strategy_version=strat.version,
                    stocks_tested=len(per_stock_results),
                    total_trades=total_trades,
                    winning_trades=winning_trades,
                    losing_trades=losing_trades,
                    win_rate_pct=win_rate_pct,
                    average_r=avg_r,
                    total_r=round(total_r, 2),
                    profit_factor=profit_factor,
                    max_drawdown_pct=round(max_dd_overall, 2),
                    avg_holding_days=avg_holding,
                    per_stock_results=per_stock_results,
                )
                strategy_metrics.append(metric)

            # 4. Perform Signal Overlap Analysis
            overlap_res = self._analyze_signal_overlap(daily_signals_matrix)

            # 5. Format Markdown Summary & Per-Stock Tables
            summary_md = self._format_summary_table(strategy_metrics)
            per_stock_md = self._format_per_stock_table(strategy_metrics)
            overlap_md = self._format_overlap_table(overlap_res)

            report = ValidationReport(
                config=self.config,
                strategy_metrics=strategy_metrics,
                overlap_result=overlap_res,
                summary_table_md=summary_md,
                per_stock_table_md=per_stock_md,
                overlap_table_md=overlap_md,
            )
            return report

        finally:
            if should_close:
                conn.close()

    def _analyze_signal_overlap(
        self, daily_signals_matrix: Dict[Tuple[str, str], Dict[str, SignalType]]
    ) -> SignalOverlapResult:
        """Calculates buy signal overlap and strategy agreement stats."""
        strategy_buy_counts: Dict[str, int] = {}
        unique_signal_counts: Dict[str, int] = {}
        agreement_counts: Dict[int, int] = {}
        multi_agree_dates: List[Dict[str, Any]] = []

        total_buy_events = 0

        for (sym, dt), strat_map in daily_signals_matrix.items():
            buying_strats = [strat for strat, sig in strat_map.items() if sig == SignalType.BUY]
            k = len(buying_strats)

            if k > 0:
                total_buy_events += 1
                agreement_counts[k] = agreement_counts.get(k, 0) + 1

                for strat in buying_strats:
                    strategy_buy_counts[strat] = strategy_buy_counts.get(strat, 0) + 1

                if k == 1:
                    unique_strat = buying_strats[0]
                    unique_signal_counts[unique_strat] = unique_signal_counts.get(unique_strat, 0) + 1

                if k >= 2:
                    multi_agree_dates.append(
                        {
                            "symbol": sym,
                            "date": dt,
                            "agreeing_count": k,
                            "strategies": buying_strats,
                        }
                    )

        return SignalOverlapResult(
            total_buy_signals=total_buy_events,
            strategy_buy_counts=strategy_buy_counts,
            unique_signal_counts=unique_signal_counts,
            agreement_counts=agreement_counts,
            multi_agree_dates=multi_agree_dates[:20],  # sample top 20
        )

    def _format_summary_table(self, metrics: List[AggregatedStrategyMetric]) -> str:
        lines = [
            "### Strategy Comparison Summary",
            "",
            "| Strategy | Version | Stocks | Trades | Win Rate % | Avg R | Total R | Profit Factor | Max DD % | Avg Holding (Days) |",
            "|----------|---------|--------|--------|------------|-------|---------|---------------|----------|-------------------|",
        ]
        for m in metrics:
            lines.append(
                f"| {m.strategy_name} | {m.strategy_version} | {m.stocks_tested} | {m.total_trades} | "
                f"{m.win_rate_pct:.1f}% | {m.average_r:.2f} | {m.total_r:.2f} | {m.profit_factor:.2f} | "
                f"{m.max_drawdown_pct:.1f}% | {m.avg_holding_days:.1f} |"
            )
        return "\n".join(lines)

    def _format_per_stock_table(self, metrics: List[AggregatedStrategyMetric]) -> str:
        lines = [
            "### Per-Stock Breakdown",
            "",
            "| Symbol | Strategy | Trades | Win Rate % | Total R | Profit Factor | Max DD % |",
            "|--------|----------|--------|------------|---------|---------------|----------|",
        ]
        for m in metrics:
            for sym, r in sorted(m.per_stock_results.items()):
                lines.append(
                    f"| {sym} | {m.strategy_name} | {r.total_trades} | {r.win_rate_pct:.1f}% | "
                    f"{r.total_r:.2f} | {r.profit_factor:.2f} | {r.max_drawdown_percent:.1f}% |"
                )
        return "\n".join(lines)

    def _format_overlap_table(self, overlap: Optional[SignalOverlapResult]) -> str:
        if not overlap:
            return ""

        lines = [
            "### Signal Overlap & Agreement Analysis",
            "",
            "| Strategy | Total BUY Signals | Unique Signals (Solo BUY) | Uniqueness % |",
            "|----------|-------------------|--------------------------|--------------|",
        ]

        for strat, total in sorted(overlap.strategy_buy_counts.items()):
            solo = overlap.unique_signal_counts.get(strat, 0)
            uniq_pct = (solo / total * 100.0) if total > 0 else 0.0
            lines.append(f"| {strat} | {total} | {solo} | {uniq_pct:.1f}% |")

        lines.extend([
            "",
            "#### Multi-Strategy Agreement Frequency",
            "",
            "| Agreed Strategies Count | Occurrences (Symbol/Date) |",
            "|-------------------------|--------------------------|",
        ])
        for k in sorted(overlap.agreement_counts.keys()):
            lines.append(f"| {k} Strategy(ies) Agreeing | {overlap.agreement_counts[k]} |")

        return "\n".join(lines)
