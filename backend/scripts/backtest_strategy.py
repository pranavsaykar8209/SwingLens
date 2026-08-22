import argparse
import logging
from pathlib import Path
import sqlite3
import sys
from typing import Dict, List, Optional
import pandas as pd

from backend.backtest.engine import BacktestEngine
from backend.backtest.models import BacktestConfig
from backend.database.connection import get_db_connection, DEFAULT_DB_PATH
from backend.indicators.engine import get_price_history
from backend.strategies.registry import get_strategy, list_strategies

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backtest_strategy")


def run_strategy_backtest(
    strategy_name: str = "ema_pullback",
    symbol: str = "ABB",
    db_path: Path = DEFAULT_DB_PATH,
    initial_capital: float = 100000.0,
) -> None:
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        print(f"Error: Database file not found at {db_path_obj}")
        print("Please run 'python -m backend.scripts.initialize_data' first.")
        sys.exit(1)

    try:
        strategy = get_strategy(strategy_name)
    except KeyError as e:
        print(f"Error: {e}")
        print("Available strategies:")
        for s in list_strategies():
            print(f"  - {s['name']} (v{s['version']})")
        sys.exit(1)

    conn = get_db_connection(db_path_obj)
    target_symbol = symbol.strip().upper() if symbol else "ABB"
    df = get_price_history(conn, target_symbol)
    conn.close()

    if df.empty:
        print(f"Error: No historical price data found for symbol '{target_symbol}' in {db_path_obj}")
        sys.exit(1)

    df["symbol"] = target_symbol
    config = BacktestConfig(initial_capital=initial_capital)
    engine = BacktestEngine(strategy, config)

    result = engine.run({target_symbol: df})

    # Print Formatted Report
    print("==================================================")
    print(f"  {result.strategy_name} v{result.strategy_version}")
    print("==================================================")
    print(f"Target Stock         : {result.symbol}")
    print(f"Period               : {result.start_date} → {result.end_date}\n")

    print(f"Total Trades         : {result.total_trades}")
    print(f"Winning Trades       : {result.winning_trades}")
    print(f"Losing Trades        : {result.losing_trades}")
    print(f"Win Rate             : {result.win_rate:.2f}%")
    print(f"Average Win %        : {result.average_win_percent:.2f}%")
    print(f"Average Loss %       : {result.average_loss_percent:.2f}%")
    print(f"Average Trade %      : {result.average_trade_percent:.2f}%")
    print(f"Profit Factor        : {result.profit_factor:.2f}")
    print(f"Max Drawdown %       : {result.max_drawdown_percent:.2f}% (${result.max_drawdown:,.2f})")
    print(f"Avg Holding Period   : {result.average_holding_days:.1f} days")
    print(f"Max Holding Period   : {result.maximum_holding_days} days")
    print(f"Avg R Multiple       : {result.average_r_multiple:.2f}")
    print(f"Total R              : {result.total_r:.2f}")

    if result.warnings:
        print("\nWarnings / Notes:")
        for w in result.warnings:
            print(f"  - {w}")

    print("\n--------------------------------------------------")
    print("RESEARCH DISCLAIMER:")
    print("This backtest report is for analytical research purposes only.")
    print("It does NOT constitute financial advice or guarantee future trading performance.")
    print("==================================================\n")


def main():
    parser = argparse.ArgumentParser(description="SwingLens Single-Stock Backtest Runner CLI")
    parser.add_argument("--strategy", type=str, default="ema_pullback", help="Strategy name (default: ema_pullback)")
    parser.add_argument("--symbol", type=str, default="ABB", help="Stock symbol to backtest (default: ABB)")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial capital (default: 100000)")
    args = parser.parse_args()

    run_strategy_backtest(
        strategy_name=args.strategy,
        symbol=args.symbol,
        initial_capital=args.capital,
    )


if __name__ == "__main__":
    main()

