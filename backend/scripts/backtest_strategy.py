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


def load_universe_symbols(conn: sqlite3.Connection) -> List[str]:
    """Retrieves all active stock symbols from SQLite database."""
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM stocks WHERE is_active = 1 ORDER BY symbol;")
    return [r[0] for r in cursor.fetchall()]


def run_strategy_backtest(
    strategy_name: str = "ema_pullback",
    symbol: Optional[str] = "ABB",
    universe: Optional[str] = None,
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

    price_data_dict: Dict[str, pd.DataFrame] = {}

    if universe and universe.lower() == "nifty_next_50":
        symbols = load_universe_symbols(conn)
        print(f"Loading historical market data for {len(symbols)} universe constituents...\n")
        for sym in symbols:
            df = get_price_history(conn, sym)
            if not df.empty:
                df["symbol"] = sym
                price_data_dict[sym] = df
    else:
        target_symbol = symbol.strip().upper() if symbol else "ABB"
        df = get_price_history(conn, target_symbol)
        if df.empty:
            print(f"Error: No historical price data found for symbol '{target_symbol}' in {db_path_obj}")
            conn.close()
            sys.exit(1)
        df["symbol"] = target_symbol
        price_data_dict[target_symbol] = df

    conn.close()

    config = BacktestConfig(initial_capital=initial_capital)
    engine = BacktestEngine(strategy, config)

    result = engine.run(price_data_dict)

    # Print Formatted Report
    print("==================================================")
    print(f"  {result.strategy_name} v{result.strategy_version}")
    print("==================================================")
    print(f"Target/Universe      : {result.symbol_or_universe}")
    print(f"Period               : {result.start_date} → {result.end_date}\n")

    print(f"Total Trades         : {result.total_trades}")
    print(f"Winning Trades       : {result.winning_trades}")
    print(f"Losing Trades        : {result.losing_trades}")
    print(f"Win Rate             : {result.win_rate_pct:.2f}%")
    print(f"Profit Factor        : {result.profit_factor:.2f}")
    print(f"Initial Capital      : ${result.initial_capital:,.2f}")
    print(f"Final Capital        : ${result.final_capital:,.2f}")
    print(f"Net Return           : {result.total_return_pct:.2f}%")
    print(f"CAGR                 : {result.cagr_pct:.2f}%")
    print(f"Max Drawdown         : {result.max_drawdown_pct:.2f}% (${result.max_drawdown:,.2f})")
    print(f"Expectancy           : ${result.expectancy:,.2f}")
    print(f"Avg Holding Period   : {result.avg_holding_period:.1f} days")
    if result.sharpe_ratio is not None:
        print(f"Sharpe Ratio         : {result.sharpe_ratio:.2f}")

    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")

    print("\n--------------------------------------------------")
    print("RESEARCH DISCLAIMER:")
    print("This backtest report is for analytical research purposes only.")
    print("It does NOT constitute financial advice or guarantee future trading performance.")
    print("==================================================\n")


def main():
    parser = argparse.ArgumentParser(description="SwingLens Strategy Backtest Runner CLI")
    parser.add_argument("--strategy", type=str, default="ema_pullback", help="Strategy name (default: ema_pullback)")
    parser.add_argument("--symbol", type=str, default="ABB", help="Stock symbol to backtest (default: ABB)")
    parser.add_argument("--universe", type=str, default=None, help="Backtest universe (e.g. nifty_next_50)")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial capital (default: 100000)")
    args = parser.parse_args()

    run_strategy_backtest(
        strategy_name=args.strategy,
        symbol=args.symbol,
        universe=args.universe,
        initial_capital=args.capital,
    )


if __name__ == "__main__":
    main()
