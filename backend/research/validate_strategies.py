import argparse
import sys
from backend.research.validator import ValidationConfig, StrategyValidator


def main():
    parser = argparse.ArgumentParser(
        description="SwingLens Strategy Representative Validation CLI"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Optional list of stock symbols to evaluate (e.g. BANKBARODA CHOLAFIN DIVISLAB)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Optional start date YYYY-MM-DD (e.g. 2024-01-01 for 2-year backtest)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Optional end date YYYY-MM-DD",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=None,
        help="Optional list of strategy names to evaluate",
    )

    args = parser.parse_args()

    config = ValidationConfig(
        symbols=args.symbols if args.symbols else ValidationConfig().symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        strategies=args.strategies,
    )

    print("==========================================================================", flush=True)
    print("           SwingLens Representative Strategy Validation Engine            ", flush=True)
    print("==========================================================================", flush=True)
    print(f"Sample Symbols ({len(config.symbols)}): {', '.join(config.symbols)}", flush=True)
    if config.start_date or config.end_date:
        print(f"Date Range: {config.start_date or 'Earliest'} to {config.end_date or 'Latest'}", flush=True)
    print("Executing lightweight validation run over SQLite historical data...\n", flush=True)

    validator = StrategyValidator(config)
    report = validator.run()

    print(report.summary_table_md, flush=True)
    print("\n" + "=" * 74 + "\n", flush=True)
    print(report.overlap_table_md, flush=True)
    print("\n" + "=" * 74 + "\n", flush=True)
    print(report.per_stock_table_md, flush=True)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
