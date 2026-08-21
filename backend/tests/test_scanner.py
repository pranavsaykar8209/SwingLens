import json
import sqlite3
from typing import List, Optional
import numpy as np
import pandas as pd
import pytest

from backend.database.connection import init_db
from backend.market_data.membership import update_index_constituents
from backend.scanner import MarketScanner, ScanResult, ScanSignalType, ScanSummary, get_active_universe_constituents
from backend.strategies.base import BaseStrategy
from backend.strategies.models import SignalType, StrategySignal
from backend.strategies.registry import register_strategy


# ---------------------------------------------------------------------------
# Test Fixtures & Mock Strategies
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_db():
    """Provides an initialized SQLite in-memory database."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    # Initialize schema
    init_db(db_path=":memory:")

    # Reuse helper schema setup on memory connection
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            ticker TEXT NOT NULL UNIQUE,
            company_name TEXT,
            exchange TEXT,
            series TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME,
            updated_at DATETIME
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            stock_id INTEGER NOT NULL,
            trade_date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adjusted_close REAL,
            volume INTEGER,
            created_at DATETIME,
            PRIMARY KEY (stock_id, trade_date),
            FOREIGN KEY (stock_id) REFERENCES stocks(id)
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS index_memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            index_name TEXT NOT NULL,
            stock_id INTEGER NOT NULL,
            valid_from DATE NOT NULL,
            valid_to DATE NULL,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY (stock_id) REFERENCES stocks(id),
            UNIQUE(index_name, stock_id, valid_from)
        );
    """)
    conn.commit()
    yield conn
    conn.close()


def insert_dummy_stock(conn: sqlite3.Connection, symbol: str, company_name: str) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO stocks (symbol, ticker, company_name, exchange, series) VALUES (?, ?, ?, 'NSE', 'EQ');",
        (symbol, f"{symbol}.NS", company_name),
    )
    stock_id = cursor.lastrowid
    conn.commit()
    return stock_id


def insert_index_member(
    conn: sqlite3.Connection,
    stock_id: int,
    index_name: str = "NIFTY_NEXT_50",
    valid_from: str = "2024-01-01",
    valid_to: Optional[str] = None,
):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO index_memberships (index_name, stock_id, valid_from, valid_to) VALUES (?, ?, ?, ?);",
        (index_name, stock_id, valid_from, valid_to),
    )
    conn.commit()


def insert_dummy_prices(conn: sqlite3.Connection, stock_id: int, num_candles: int = 250, start_date: str = "2024-01-01"):
    cursor = conn.cursor()
    dates = pd.date_range(start=start_date, periods=num_candles, freq="B").strftime("%Y-%m-%d")
    base_price = 100.0

    for idx, d in enumerate(dates):
        close_p = base_price + idx * 0.5
        open_p = close_p - 0.2
        high_p = close_p + 1.0
        low_p = close_p - 1.0
        vol = 100000 + idx * 500
        cursor.execute(
            """
            INSERT INTO daily_prices (stock_id, trade_date, open, high, low, close, adjusted_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (stock_id, d, open_p, high_p, low_p, close_p, close_p, vol),
        )
    conn.commit()


class MockWatchStrategy(BaseStrategy):
    name = "Mock Watch Strategy"
    version = "1.0"
    required_indicators = ["ema_20"]

    def generate_signals(self, df: pd.DataFrame) -> List[StrategySignal]:
        symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "TEST"
        trade_date = str(df["trade_date"].iloc[-1])
        return [
            StrategySignal(
                symbol=symbol,
                strategy_name=self.name,
                strategy_version=self.version,
                signal=SignalType.WATCH,
                signal_date=trade_date,
                reason="Watch condition triggered",
            )
        ]


# ---------------------------------------------------------------------------
# Test Cases (1 to 15)
# ---------------------------------------------------------------------------

def test_1_universe_loading(memory_db):
    """1. Test loading current Nifty Next 50 universe dynamically."""
    stock1 = insert_dummy_stock(memory_db, "STOCK1", "Stock One")
    stock2 = insert_dummy_stock(memory_db, "STOCK2", "Stock Two")
    insert_index_member(memory_db, stock1, "NIFTY_NEXT_50")
    insert_index_member(memory_db, stock2, "NIFTY_NEXT_50")

    constituents = get_active_universe_constituents(memory_db, index_name="NIFTY_NEXT_50")
    symbols = [c["symbol"] for c in constituents]
    assert len(symbols) == 2
    assert "STOCK1" in symbols
    assert "STOCK2" in symbols


def test_2_scanner_processes_all_members(memory_db):
    """2. Test scanner processes all current members of the index."""
    s1 = insert_dummy_stock(memory_db, "ABC", "ABC Corp")
    s2 = insert_dummy_stock(memory_db, "XYZ", "XYZ Ltd")
    insert_index_member(memory_db, s1)
    insert_index_member(memory_db, s2)
    insert_dummy_prices(memory_db, s1, num_candles=250)
    insert_dummy_prices(memory_db, s2, num_candles=250)

    scanner = MarketScanner()
    results = scanner.scan(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)
    assert len(results) == 2
    scanned_symbols = {r.symbol for r in results}
    assert scanned_symbols == {"ABC", "XYZ"}


def test_3_scanner_uses_latest_completed_candle(memory_db):
    """3. Test scanner evaluates the latest completed candle date and close price."""
    s1 = insert_dummy_stock(memory_db, "TEST1", "Test Company")
    insert_index_member(memory_db, s1)
    insert_dummy_prices(memory_db, s1, num_candles=250, start_date="2024-01-01")

    # Get expected latest date and close from DB
    cursor = memory_db.cursor()
    cursor.execute("SELECT trade_date, close FROM daily_prices WHERE stock_id = ? ORDER BY trade_date DESC LIMIT 1;", (s1,))
    row = cursor.fetchone()
    expected_date = row["trade_date"]
    expected_close = row["close"]

    scanner = MarketScanner()
    results = scanner.scan(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)
    assert len(results) == 1
    assert results[0].signal_date == expected_date
    assert results[0].close == round(expected_close, 2)


def test_4_buy_result_when_strategy_returns_buy(memory_db):
    """4. Test BUY ScanResult populated correctly when strategy signals BUY."""
    s1 = insert_dummy_stock(memory_db, "BUYSTOCK", "Buy Stock Inc")
    insert_index_member(memory_db, s1)

    # Generate synthetic price history designed to trigger EMA Pullback BUY:
    # Strong uptrend: EMA20 > EMA50 > EMA200
    dates = pd.date_range(start="2024-01-01", periods=250, freq="B").strftime("%Y-%m-%d")
    cursor = memory_db.cursor()
    base_price = 100.0

    for idx, d in enumerate(dates):
        close_p = base_price + idx * 2.0  # Steady uptrend
        if idx == 248:
            high_p = close_p + 1.0
            low_p = close_p - 1.0
            open_p = close_p
        elif idx == 249:  # Latest candle setup
            # pull back near EMA20, close > prev high
            high_p = close_p + 5.0
            low_p = close_p - 0.5
            open_p = close_p - 0.2
        else:
            high_p = close_p + 1.0
            low_p = close_p - 1.0
            open_p = close_p - 0.2
        vol = 500000

        cursor.execute(
            "INSERT INTO daily_prices (stock_id, trade_date, open, high, low, close, adjusted_close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (s1, d, open_p, high_p, low_p, close_p, close_p, vol),
        )
    memory_db.commit()

    scanner = MarketScanner()
    results = scanner.scan(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)
    assert len(results) == 1
    # Check signal object structure
    res = results[0]
    assert res.symbol == "BUYSTOCK"
    assert res.status == "SUCCESS"
    assert res.signal in [ScanSignalType.BUY, ScanSignalType.HOLD]


def test_5_hold_result_when_strategy_returns_hold(memory_db):
    """5. Test HOLD ScanResult when strategy rules are not met."""
    s1 = insert_dummy_stock(memory_db, "FLATSTOCK", "Flat Stock Ltd")
    insert_index_member(memory_db, s1)
    insert_dummy_prices(memory_db, s1, num_candles=250)

    scanner = MarketScanner()
    results = scanner.scan(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)
    assert len(results) == 1
    assert results[0].signal == ScanSignalType.HOLD
    assert results[0].status == "SUCCESS"


def test_6_watch_result_when_strategy_returns_watch(memory_db):
    """6. Test WATCH ScanResult when strategy returns WATCH."""
    s1 = insert_dummy_stock(memory_db, "WATCHSTOCK", "Watch Stock Co")
    insert_index_member(memory_db, s1)
    insert_dummy_prices(memory_db, s1, num_candles=250)

    scanner = MarketScanner()
    watch_strat = MockWatchStrategy()
    results = scanner.scan(index_name="NIFTY_NEXT_50", strategy_name=watch_strat, conn=memory_db)
    assert len(results) == 1
    assert results[0].signal == ScanSignalType.WATCH
    assert results[0].status == "SUCCESS"


def test_7_error_result_for_insufficient_data(memory_db):
    """7. Test ERROR ScanResult returned when stock has insufficient data (<200 candles)."""
    s1 = insert_dummy_stock(memory_db, "SHORTDATA", "Short Data Inc")
    insert_index_member(memory_db, s1)
    insert_dummy_prices(memory_db, s1, num_candles=50)  # Only 50 candles

    scanner = MarketScanner()
    results = scanner.scan(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", min_required_candles=200, conn=memory_db)
    assert len(results) == 1
    assert results[0].signal == ScanSignalType.ERROR
    assert results[0].status == "ERROR"
    assert "Insufficient historical data" in results[0].error


def test_8_one_failed_stock_does_not_stop_entire_scan(memory_db):
    """8. Test that a failure on one stock does not abort scanning remaining stocks."""
    s1 = insert_dummy_stock(memory_db, "BADSTOCK", "Bad Stock Co")
    s2 = insert_dummy_stock(memory_db, "GOODSTOCK", "Good Stock Co")
    insert_index_member(memory_db, s1)
    insert_index_member(memory_db, s2)

    insert_dummy_prices(memory_db, s1, num_candles=20)  # Will fail warm-up
    insert_dummy_prices(memory_db, s2, num_candles=250)  # Sufficient history

    scanner = MarketScanner()
    summary = scanner.scan_summary(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)

    assert summary.scanned_count == 2
    assert summary.error_count == 1
    assert summary.hold_count + summary.buy_count + summary.watch_count == 1

    res_map = {r.symbol: r for r in summary.results}
    assert res_map["BADSTOCK"].signal == ScanSignalType.ERROR
    assert res_map["GOODSTOCK"].status == "SUCCESS"


def test_9_scanner_does_not_download_data(memory_db, monkeypatch):
    """9. Test scanner operates offline without executing network downloads."""
    s1 = insert_dummy_stock(memory_db, "OFFLINE", "Offline Test Ltd")
    insert_index_member(memory_db, s1)
    insert_dummy_prices(memory_db, s1, num_candles=250)

    # Monkeypatch downloader functions to raise Exception if invoked
    def raise_on_download(*args, **kwargs):
        pytest.fail("Scanner attempted to invoke market data downloader!")

    monkeypatch.setattr("httpx.get", raise_on_download)

    scanner = MarketScanner()
    results = scanner.scan(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)
    assert len(results) == 1
    assert results[0].symbol == "OFFLINE"


def test_10_scanner_does_not_modify_daily_prices(memory_db):
    """10. Test scanning does not mutate daily_prices in database."""
    s1 = insert_dummy_stock(memory_db, "IMMUTABLE", "Immutable Co")
    insert_index_member(memory_db, s1)
    insert_dummy_prices(memory_db, s1, num_candles=250)

    cursor = memory_db.cursor()
    cursor.execute("SELECT COUNT(*), SUM(close) FROM daily_prices;")
    count_before, sum_before = cursor.fetchone()

    scanner = MarketScanner()
    scanner.scan(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)

    cursor.execute("SELECT COUNT(*), SUM(close) FROM daily_prices;")
    count_after, sum_after = cursor.fetchone()

    assert count_before == count_after
    assert sum_before == sum_after


def test_11_scanner_does_not_modify_strategy_parameters(memory_db):
    """11. Test strategy default parameters remain unchanged after scan."""
    s1 = insert_dummy_stock(memory_db, "PARAMTEST", "Param Test Ltd")
    insert_index_member(memory_db, s1)
    insert_dummy_prices(memory_db, s1, num_candles=250)

    scanner = MarketScanner()
    strat = scanner.scan(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)

    from backend.strategies.registry import get_strategy
    strat_instance = get_strategy("ema_pullback")
    assert strat_instance.parameters["ema_fast"] == 20
    assert strat_instance.parameters["ema_long"] == 200


def test_12_empty_buy_result_is_valid(memory_db):
    """12. Test that a scan yielding 0 BUY signals produces a valid result."""
    s1 = insert_dummy_stock(memory_db, "NOBUY", "No Buy Corp")
    insert_index_member(memory_db, s1)
    insert_dummy_prices(memory_db, s1, num_candles=250)

    scanner = MarketScanner()
    summary = scanner.scan_summary(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)
    assert summary.buy_count == 0
    assert summary.scanned_count == 1
    assert summary.results[0].signal == ScanSignalType.HOLD


def test_13_current_index_membership_is_respected(memory_db):
    """13. Test that inactive index members (valid_to is set) are excluded."""
    active_stock = insert_dummy_stock(memory_db, "ACTIVE", "Active Member")
    inactive_stock = insert_dummy_stock(memory_db, "INACTIVE", "Inactive Member")

    insert_index_member(memory_db, active_stock, valid_from="2024-01-01", valid_to=None)
    insert_index_member(memory_db, inactive_stock, valid_from="2024-01-01", valid_to="2024-06-01")

    insert_dummy_prices(memory_db, active_stock, num_candles=250)
    insert_dummy_prices(memory_db, inactive_stock, num_candles=250)

    scanner = MarketScanner()
    results = scanner.scan(index_name="NIFTY_NEXT_50", strategy_name="ema_pullback", conn=memory_db)
    symbols = [r.symbol for r in results]
    assert "ACTIVE" in symbols
    assert "INACTIVE" not in symbols


def test_14_no_lookahead_behavior(memory_db):
    """14. Test as_of_date restricts scan strictly to historical candles up to that date."""
    s1 = insert_dummy_stock(memory_db, "TIMEWARP", "Time Warp Inc")
    insert_index_member(memory_db, s1)

    # Insert price history spanning Jan 2024 to Aug 2024
    dates = pd.date_range(start="2024-01-01", end="2024-08-01", freq="B").strftime("%Y-%m-%d")
    cursor = memory_db.cursor()
    for idx, d in enumerate(dates):
        close_p = 100.0 + idx * 0.1
        cursor.execute(
            "INSERT INTO daily_prices (stock_id, trade_date, open, high, low, close, adjusted_close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (s1, d, close_p, close_p + 0.5, close_p - 0.5, close_p, close_p, 100000),
        )
    memory_db.commit()

    cutoff_date = dates[150]  # Candle #150

    scanner = MarketScanner()
    results = scanner.scan(
        index_name="NIFTY_NEXT_50",
        strategy_name="ema_pullback",
        as_of_date=cutoff_date,
        min_required_candles=100,
        conn=memory_db,
    )
    assert len(results) == 1
    assert results[0].signal_date == cutoff_date


def test_15_scan_result_serialization():
    """15. Test ScanResult and ScanSummary model serialization to dict/JSON (FastAPI compatibility)."""
    res = ScanResult(
        symbol="TEST",
        company_name="Test Company",
        signal=ScanSignalType.BUY,
        signal_date="2026-08-20",
        close=150.50,
        entry_price=150.50,
        stop_loss=140.00,
        target_price=171.50,
        risk_reward=2.0,
        score=0.85,
        strategy_name="EMA Pullback",
        strategy_version="1.0",
        reason="Uptrend pullback confirmed",
        metadata={"rsi14": 58.2},
        error=None,
        status="SUCCESS",
    )

    data_dict = res.model_dump()
    assert data_dict["symbol"] == "TEST"
    assert data_dict["signal"] == "BUY"
    assert data_dict["risk_reward"] == 2.0

    json_str = res.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["symbol"] == "TEST"
    assert parsed["signal"] == "BUY"

    summary = ScanSummary(
        scan_date="2026-08-20",
        universe="NIFTY_NEXT_50",
        strategy="EMA Pullback",
        strategy_version="1.0",
        scanned_count=1,
        buy_count=1,
        watch_count=0,
        hold_count=0,
        error_count=0,
        results=[res],
    )
    summary_json = summary.model_dump_json()
    assert "NIFTY_NEXT_50" in summary_json
