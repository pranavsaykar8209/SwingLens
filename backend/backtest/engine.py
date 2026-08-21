from typing import Any, Dict, List, Optional, Union
import pandas as pd

from backend.indicators import calculate_indicators
from backend.strategies.base import BaseStrategy
from backend.strategies.models import SignalType, StrategySignal
from .metrics import calculate_performance_metrics
from .models import BacktestConfig, BacktestResult, ExitReason
from .portfolio import Portfolio


class BacktestEngine:
    """
    Reusable, event-driven Backtesting Engine.
    Executes trading strategies candle-by-candle with execution modeling,
    transaction costs, slippage, and performance analytics.
    """

    def __init__(self, strategy: BaseStrategy, config: Optional[BacktestConfig] = None):
        self.strategy = strategy
        self.config = config or BacktestConfig()

    def run(
        self, price_data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]
    ) -> BacktestResult:
        """
        Executes the backtest over single or multi-stock price DataFrames.

        Parameters:
        - price_data: Single DataFrame or Dict of DataFrames keyed by symbol.

        Returns:
        - BacktestResult containing summary metrics, trades, equity curve, and warnings.
        """
        warnings: List[str] = []

        # Standardize input to Dict[str, DataFrame]
        if isinstance(price_data, pd.DataFrame):
            sym = price_data["symbol"].iloc[0] if "symbol" in price_data.columns else "UNKNOWN"
            data_dict = {sym: price_data.copy()}
            universe_label = sym
        else:
            data_dict = {k: v.copy() for k, v in price_data.items()}
            universe_label = f"Multi-Stock Universe ({len(data_dict)} stocks)"

        if not data_dict:
            warnings.append("Empty price data provided.")
            return self._empty_result(universe_label, warnings)

        # 1. Compute required strategy indicators on each DataFrame
        processed_data: Dict[str, pd.DataFrame] = {}
        for sym, df in data_dict.items():
            if df.empty:
                continue
            df_sorted = df.sort_values("trade_date").reset_index(drop=True)
            if self.strategy.required_indicators:
                df_sorted = calculate_indicators(df_sorted, self.strategy.required_indicators)
            processed_data[sym] = df_sorted

        if not processed_data:
            warnings.append("All provided price DataFrames were empty.")
            return self._empty_result(universe_label, warnings)

        # 2. Extract master timeline of unique trade_dates across all stocks
        all_dates = set()
        for df in processed_data.values():
            all_dates.update(df["trade_date"].tolist())
        timeline = sorted(list(all_dates))

        if len(timeline) < 2:
            warnings.append("Insufficient trade dates for backtesting.")
            return self._empty_result(universe_label, warnings)

        start_date = timeline[0]
        end_date = timeline[-1]

        # General warnings check
        warnings.append("Survivorship Bias Note: Historical backtests using static universes reflect survivorship bias.")

        portfolio = Portfolio(self.config)
        pending_signals: Dict[str, StrategySignal] = {}
        stock_date_indices: Dict[str, Dict[str, int]] = {
            sym: {date: idx for idx, date in enumerate(df["trade_date"])}
            for sym, df in processed_data.items()
        }

        ambiguity_count = 0

        # 3. Candle-by-candle simulation loop
        for t_idx, current_date in enumerate(timeline):
            current_prices: Dict[str, float] = {}

            # Populate current_prices map
            for sym, df in processed_data.items():
                if current_date in stock_date_indices[sym]:
                    idx = stock_date_indices[sym][current_date]
                    current_prices[sym] = float(df["close"].iloc[idx])

            # STEP A: Execute pending entry signals from previous candle at CURRENT OPEN
            for sym in list(pending_signals.keys()):
                sig = pending_signals.pop(sym)
                if sym in stock_date_indices and current_date in stock_date_indices[sym]:
                    idx = stock_date_indices[sym][current_date]
                    curr_row = processed_data[sym].iloc[idx]
                    open_price = float(curr_row["open"])

                    if sig.signal == SignalType.BUY and portfolio.can_open_position(sym):
                        curr_equity = portfolio.get_equity(current_prices)
                        qty = portfolio.calculate_quantity(open_price, sig.stop_loss, curr_equity)
                        if qty > 0:
                            portfolio.open_position(
                                symbol=sym,
                                strategy_name=self.strategy.name,
                                strategy_version=self.strategy.version,
                                entry_date=current_date,
                                raw_price=open_price,
                                quantity=qty,
                                stop_loss=sig.stop_loss,
                                target_price=sig.target_price,
                            )
                    elif sig.signal == SignalType.SELL and sym in portfolio.open_positions:
                        pos = portfolio.open_positions[sym]
                        entry_idx = stock_date_indices[sym].get(pos.entry_date, idx)
                        holding_period = idx - entry_idx
                        portfolio.close_position(
                            symbol=sym,
                            exit_date=current_date,
                            raw_price=open_price,
                            exit_reason=ExitReason.SIGNAL.value,
                            holding_period=holding_period,
                        )

            # STEP B: Monitor Open Positions for Stop-Loss & Target hits during current candle (OHLC)
            for sym in list(portfolio.open_positions.keys()):
                pos = portfolio.open_positions[sym]
                if current_date in stock_date_indices[sym]:
                    idx = stock_date_indices[sym][current_date]
                    row = processed_data[sym].iloc[idx]
                    high_p = float(row["high"])
                    low_p = float(row["low"])
                    open_p = float(row["open"])

                    stop_hit = pos.stop_loss is not None and low_p <= pos.stop_loss
                    target_hit = pos.target_price is not None and high_p >= pos.target_price

                    entry_idx = stock_date_indices[sym].get(pos.entry_date, idx)
                    holding_period = idx - entry_idx

                    if stop_hit and target_hit:
                        ambiguity_count += 1
                        if self.config.ambiguity_policy == "conservative":
                            exit_p = pos.stop_loss if pos.stop_loss else low_p
                            portfolio.close_position(
                                symbol=sym,
                                exit_date=current_date,
                                raw_price=exit_p,
                                exit_reason=ExitReason.STOP_LOSS.value,
                                holding_period=holding_period,
                            )
                        elif self.config.ambiguity_policy == "optimistic":
                            exit_p = pos.target_price if pos.target_price else high_p
                            portfolio.close_position(
                                symbol=sym,
                                exit_date=current_date,
                                raw_price=exit_p,
                                exit_reason=ExitReason.TARGET.value,
                                holding_period=holding_period,
                            )
                        else:  # skip / flag
                            exit_p = pos.stop_loss if pos.stop_loss else low_p
                            portfolio.close_position(
                                symbol=sym,
                                exit_date=current_date,
                                raw_price=exit_p,
                                exit_reason=ExitReason.STOP_LOSS.value,
                                holding_period=holding_period,
                            )

                    elif stop_hit:
                        exit_p = pos.stop_loss if pos.stop_loss else low_p
                        portfolio.close_position(
                            symbol=sym,
                            exit_date=current_date,
                            raw_price=exit_p,
                            exit_reason=ExitReason.STOP_LOSS.value,
                            holding_period=holding_period,
                        )
                    elif target_hit:
                        exit_p = pos.target_price if pos.target_price else high_p
                        portfolio.close_position(
                            symbol=sym,
                            exit_date=current_date,
                            raw_price=exit_p,
                            exit_reason=ExitReason.TARGET.value,
                            holding_period=holding_period,
                        )

            # STEP C: Generate Strategy Signals at CLOSE of Candle N (using df.iloc[:idx+1])
            for sym, df in processed_data.items():
                if current_date in stock_date_indices[sym]:
                    idx = stock_date_indices[sym][current_date]
                    # NO LOOK-AHEAD: Pass only slice up to current candle idx
                    sub_df = df.iloc[: idx + 1]
                    sig = self.strategy.generate_latest_signal(sub_df)
                    if sig and sig.signal in [SignalType.BUY, SignalType.SELL]:
                        pending_signals[sym] = sig

            # STEP D: Record Daily Equity State
            portfolio.record_daily_equity(current_date, current_prices)

        # 4. Close any open positions at end of backtest
        final_date = timeline[-1]
        for sym in list(portfolio.open_positions.keys()):
            pos = portfolio.open_positions[sym]
            idx = stock_date_indices[sym].get(final_date, len(processed_data[sym]) - 1)
            final_row = processed_data[sym].iloc[idx]
            close_price = float(final_row["close"])
            entry_idx = stock_date_indices[sym].get(pos.entry_date, 0)
            holding_period = idx - entry_idx

            portfolio.close_position(
                symbol=sym,
                exit_date=final_date,
                raw_price=close_price,
                exit_reason=ExitReason.END_OF_BACKTEST.value,
                holding_period=holding_period,
            )

        if ambiguity_count > 0:
            warnings.append(
                f"Ambiguity Warning: {ambiguity_count} trade(s) touched both Stop Loss & Target on the same daily candle (Policy: '{self.config.ambiguity_policy}')."
            )

        if len(portfolio.closed_trades) < 5:
            warnings.append("Sample Size Warning: Very small number of trades executed (< 5). Metrics may be statistically uninformative.")

        # 5. Calculate final performance metrics
        metrics = calculate_performance_metrics(
            initial_capital=self.config.initial_capital,
            final_capital=portfolio.cash,
            closed_trades=portfolio.closed_trades,
            equity_curve=portfolio.equity_curve,
            start_date=start_date,
            end_date=end_date,
        )

        return BacktestResult(
            strategy_name=self.strategy.name,
            strategy_version=self.strategy.version,
            symbol_or_universe=universe_label,
            start_date=start_date,
            end_date=end_date,
            initial_capital=metrics["initial_capital"],
            final_capital=metrics["final_capital"],
            total_return_pct=metrics["total_return_pct"],
            cagr_pct=metrics["cagr_pct"],
            total_trades=metrics["total_trades"],
            winning_trades=metrics["winning_trades"],
            losing_trades=metrics["losing_trades"],
            win_rate_pct=metrics["win_rate_pct"],
            profit_factor=metrics["profit_factor"],
            max_drawdown=metrics["max_drawdown"],
            max_drawdown_pct=metrics["max_drawdown_pct"],
            expectancy=metrics["expectancy"],
            avg_holding_period=metrics["avg_holding_period"],
            sharpe_ratio=metrics["sharpe_ratio"],
            sortino_ratio=metrics["sortino_ratio"],
            trades=portfolio.closed_trades,
            equity_curve=portfolio.equity_curve,
            warnings=warnings,
        )

    def _empty_result(self, label: str, warnings: List[str]) -> BacktestResult:
        return BacktestResult(
            strategy_name=self.strategy.name,
            strategy_version=self.strategy.version,
            symbol_or_universe=label,
            start_date="N/A",
            end_date="N/A",
            initial_capital=self.config.initial_capital,
            final_capital=self.config.initial_capital,
            total_return_pct=0.0,
            cagr_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate_pct=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
            expectancy=0.0,
            avg_holding_period=0.0,
            warnings=warnings,
        )
