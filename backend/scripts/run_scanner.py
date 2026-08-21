#!/usr/bin/env python3
"""
Developer CLI runner for SwingLens Daily Market Scanner.

Execution:
    PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.run_scanner
"""

import sys
from backend.scanner import MarketScanner, ScanSignalType


def main() -> None:
    scanner = MarketScanner()
    summary = scanner.scan_summary(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback")

    print("SwingLens Scanner")
    print("=================")
    print()
    print(f"Date: {summary.scan_date}")
    print(f"Universe: {summary.universe}")
    print(f"Strategy: {summary.strategy} v{summary.strategy_version}")
    print()
    print(f"Stocks scanned: {summary.scanned_count}")
    print(f"BUY: {summary.buy_count}")
    print(f"WATCH: {summary.watch_count}")
    print(f"HOLD: {summary.hold_count}")
    print(f"ERROR: {summary.error_count}")
    print()
    print("BUY SIGNALS:")

    buy_results = [r for r in summary.results if r.signal == ScanSignalType.BUY]
    if buy_results:
        for res in buy_results:
            company_info = f" ({res.company_name})" if res.company_name else ""
            print(f"- {res.symbol}{company_info} | Entry: {res.entry_price} | SL: {res.stop_loss} | Target: {res.target_price} | R:R: {res.risk_reward}")
    else:
        print("None")


if __name__ == "__main__":
    main()
