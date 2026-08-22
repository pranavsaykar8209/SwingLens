"""
Comprehensive test suite for Persisted Daily Scan Results and Historical Scans.
"""
import sqlite3
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.database.connection import init_db, get_db_connection
from backend.ranking.models import DailySignalRanking, RankedSignal, SignalTier
from backend.aggregator.models import AggregatedSignalStrength
from backend.ranking.storage import (
    persist_daily_scan_ranking,
    get_persisted_daily_ranking,
    get_historical_scan_summaries,
)
from backend.scanner.daily_workflow import run_daily_scan_workflow, get_daily_scan_status


@pytest.fixture
def test_db_path(tmp_path):
    """Provides a fresh SQLite database path with initialized tables and sample stocks."""
    db_file = tmp_path / "test_persisted.db"
    init_db(db_file)

    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    # Insert sample stocks
    cursor.execute("""
        INSERT INTO stocks (id, symbol, ticker, company_name, exchange, is_active)
        VALUES 
            (1, 'ABB', 'ABB.NS', 'ABB India Ltd.', 'NSE', 1),
            (2, 'HDFCAMC', 'HDFCAMC.NS', 'HDFC AMC Ltd.', 'NSE', 1),
            (3, 'TCS', 'TCS.NS', 'Tata Consultancy Services', 'NSE', 1);
    """)

    # Insert index memberships
    cursor.execute("""
        INSERT INTO index_memberships (index_name, stock_id, valid_from)
        VALUES 
            ('NIFTY_NEXT_50', 1, '2020-01-01'),
            ('NIFTY_NEXT_50', 2, '2020-01-01'),
            ('NIFTY_NEXT_50', 3, '2020-01-01');
    """)

    from datetime import datetime, timedelta
    base_date = datetime(2025, 1, 1)
    for stock_id in (1, 2, 3):
        for i in range(250):
            d = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT OR IGNORE INTO daily_prices (stock_id, trade_date, open, high, low, close, volume)
                VALUES (?, ?, 100.0, 105.0, 95.0, 102.0, 10000);
            """, (stock_id, d))

    conn.commit()
    conn.close()
    return db_file


def _create_mock_ranking(scan_date: str = "2026-08-20") -> DailySignalRanking:
    """Helper to create a deterministic DailySignalRanking instance."""
    sig1 = RankedSignal(
        rank=1,
        symbol="HDFCAMC",
        company_name="HDFC AMC Ltd.",
        signal_date=scan_date,
        score=3,
        strength=AggregatedSignalStrength.MODERATE,
        tier=SignalTier.MODERATE_OPPORTUNITY,
        buy_count=3,
        strategies_evaluated=5,
        strategies_total=5,
        buy_strategies=["EMA Pullback", "MACD Momentum", "Bollinger Squeeze"],
        hold_strategies=["MA Trend Breakout", "RSI Mean-Reversion"],
        error_strategies=[],
        best_strategy_name="EMA Pullback",
        best_entry_price=2600.0,
        best_stop_loss=2500.0,
        best_target_price=2800.0,
        best_risk_reward=2.0,
    )
    sig2 = RankedSignal(
        rank=2,
        symbol="ABB",
        company_name="ABB India Ltd.",
        signal_date=scan_date,
        score=0,
        strength=AggregatedSignalStrength.NO_SIGNAL,
        tier=SignalTier.WEAK_OR_NO_SIGNAL,
        buy_count=0,
        strategies_evaluated=5,
        strategies_total=5,
        buy_strategies=[],
        hold_strategies=["EMA Pullback", "MA Trend Breakout", "RSI Mean-Reversion", "MACD Momentum", "Bollinger Squeeze"],
        error_strategies=[],
        best_strategy_name=None,
        best_entry_price=None,
        best_stop_loss=None,
        best_target_price=None,
        best_risk_reward=None,
    )
    return DailySignalRanking(
        signal_date=scan_date,
        universe="NIFTY_NEXT_50",
        universe_size=2,
        evaluated_count=2,
        excluded_count=0,
        buy_signal_count=1,
        results=[sig1, sig2],
        shortlist=[sig1],
    )


def test_persist_and_get_daily_ranking(test_db_path):
    """1. Verify ranking persistence and read-only retrieval from SQLite."""
    conn = get_db_connection(test_db_path)
    ranking = _create_mock_ranking("2026-08-20")

    count = persist_daily_scan_ranking(conn, ranking, scan_run_id=1)
    assert count == 2

    # Query latest
    persisted = get_persisted_daily_ranking(conn)
    assert persisted is not None
    assert persisted.signal_date == "2026-08-20"
    assert persisted.evaluated_count == 2
    assert persisted.buy_signal_count == 1
    assert len(persisted.results) == 2
    assert persisted.results[0].symbol == "HDFCAMC"
    assert persisted.results[0].buy_strategies == ["EMA Pullback", "MACD Momentum", "Bollinger Squeeze"]
    assert persisted.results[0].best_entry_price == 2600.0
    assert persisted.results[1].symbol == "ABB"
    assert persisted.results[1].buy_count == 0

    conn.close()


def test_unique_constraint_prevents_duplicate_daily_results(test_db_path):
    """2. Verify unique constraint and idempotency on (scan_date, stock_id)."""
    conn = get_db_connection(test_db_path)
    ranking = _create_mock_ranking("2026-08-20")

    # First insert
    count1 = persist_daily_scan_ranking(conn, ranking)
    assert count1 == 2

    # Second insert updates without creating duplicate rows
    count2 = persist_daily_scan_ranking(conn, ranking)
    assert count2 == 2

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_scan_results WHERE scan_date = '2026-08-20';")
    total_rows = cursor.fetchone()[0]
    assert total_rows == 2

    conn.close()


def test_historical_scans_summaries_and_immutability(test_db_path):
    """3. Verify historical scan summaries list and snapshot immutability across multiple dates."""
    conn = get_db_connection(test_db_path)

    # Persist Date 1
    ranking1 = _create_mock_ranking("2026-08-19")
    persist_daily_scan_ranking(conn, ranking1)

    # Persist Date 2
    ranking2 = _create_mock_ranking("2026-08-20")
    persist_daily_scan_ranking(conn, ranking2)

    # History summary list
    history = get_historical_scan_summaries(conn)
    assert len(history) == 2
    assert history[0]["scan_date"] == "2026-08-20"
    assert history[0]["buy_setups"] == 1
    assert history[1]["scan_date"] == "2026-08-19"

    # Specific date retrieval
    aug19 = get_persisted_daily_ranking(conn, scan_date="2026-08-19")
    assert aug19 is not None
    assert aug19.signal_date == "2026-08-19"

    aug20 = get_persisted_daily_ranking(conn, scan_date="2026-08-20")
    assert aug20 is not None
    assert aug20.signal_date == "2026-08-20"

    conn.close()


def test_api_daily_signals_read_only_endpoint(test_db_path, monkeypatch):
    """4. Verify GET /api/daily-signals is 100% read-only and returns 404 when NOT run."""
    monkeypatch.setattr("backend.database.connection.DEFAULT_DB_PATH", test_db_path)
    client = TestClient(app)

    # Case A: Before any scan is run -> 404
    resp_empty = client.get("/api/daily-signals")
    assert resp_empty.status_code == 404
    assert "No persisted daily scan results found" in resp_empty.json()["detail"]

    # Case B: Persist results directly
    conn = get_db_connection(test_db_path)
    ranking = _create_mock_ranking("2026-08-20")
    persist_daily_scan_ranking(conn, ranking)
    conn.close()

    # Case C: Read from SQLite (without triggering ranker)
    with patch("backend.ranking.ranker.DailySignalRanker.run") as mock_ranker:
        resp_loaded = client.get("/api/daily-signals")
        assert resp_loaded.status_code == 200
        data = resp_loaded.json()
        assert data["signal_date"] == "2026-08-20"
        assert len(data["results"]) == 2
        assert data["buy_signal_count"] == 1
        # Proves zero strategy calculation occurred on GET request
        mock_ranker.assert_not_called()


def test_api_historical_scan_endpoints(test_db_path, monkeypatch):
    """5. Verify GET /api/daily-signals/history and GET /api/daily-signals/{scan_date}."""
    monkeypatch.setattr("backend.database.connection.DEFAULT_DB_PATH", test_db_path)
    client = TestClient(app)

    conn = get_db_connection(test_db_path)
    persist_daily_scan_ranking(conn, _create_mock_ranking("2026-08-19"))
    persist_daily_scan_ranking(conn, _create_mock_ranking("2026-08-20"))
    conn.close()

    # History list
    history_resp = client.get("/api/daily-signals/history")
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert len(history_data) >= 2
    assert history_data[0]["scan_date"] == "2026-08-20"

    # Query specific date
    date_resp = client.get("/api/daily-signals/2026-08-19")
    assert date_resp.status_code == 200
    date_data = date_resp.json()
    assert date_data["signal_date"] == "2026-08-19"

    # Query non-existent date -> 404
    missing_resp = client.get("/api/daily-signals/1999-01-01")
    assert missing_resp.status_code == 404


def test_daily_scan_workflow_persists_ranking_and_is_idempotent(test_db_path, monkeypatch):
    """6. Verify run_daily_scan_workflow executes ranking once and second call is idempotent."""
    monkeypatch.setattr("backend.database.connection.DEFAULT_DB_PATH", test_db_path)

    with patch("backend.scanner.daily_workflow.run_market_data_update") as mock_update:
        summary1 = run_daily_scan_workflow(universe="NIFTY_NEXT_50", force=False, db_path=test_db_path)
        assert summary1 is not None
        assert mock_update.call_count == 1

        # Check that daily_scan_results now has rows
        conn = get_db_connection(test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daily_scan_results;")
        count = cursor.fetchone()[0]
        assert count > 0
        conn.close()

        # Second call with force=False must NOT run market update or ranker again
        summary2 = run_daily_scan_workflow(universe="NIFTY_NEXT_50", force=False, db_path=test_db_path)
        assert summary2 is not None
        assert mock_update.call_count == 1  # Still 1, proving zero re-run

