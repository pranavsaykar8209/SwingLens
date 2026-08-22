import sqlite3
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.database.connection import get_db_connection, init_db
from backend.scanner.daily_workflow import (
    get_daily_scan_status,
    run_daily_scan_workflow,
)

client = TestClient(app)


def test_daily_scan_status_not_run():
    response = client.get("/api/daily-scan/status?universe=NIFTY_NEXT_50&strategy=ema_pullback")
    assert response.status_code == 200
    data = response.json()
    assert "scan_date" in data
    assert "already_completed" in data
    assert "status" in data


def test_daily_scan_run_workflow_idempotency(tmp_path):
    test_db = tmp_path / "test_swinglens.db"
    init_db(test_db)

    # 1. First status check: NOT_RUN
    status1 = get_daily_scan_status(db_path=test_db)
    assert status1["already_completed"] is False
    assert status1["status"] in ("NOT_RUN", "RUNNING")

    # Mock market data update to prevent yfinance network calls during unit test
    with patch("backend.scanner.daily_workflow.run_market_data_update") as mock_update:
        # 2. First run (force=False) -> Executes scan & creates COMPLETED record
        summary1 = run_daily_scan_workflow(force=False, db_path=test_db)
        assert summary1 is not None
        assert mock_update.called

        # 3. Second status check -> COMPLETED
        status2 = get_daily_scan_status(db_path=test_db)
        assert status2["already_completed"] is True
        assert status2["status"] == "COMPLETED"

        # Reset mock call count
        mock_update.reset_mock()

        # 4. Second run (force=False) -> Skips market data update and returns cached scan
        summary2 = run_daily_scan_workflow(force=False, db_path=test_db)
        assert summary2.scan_date == summary1.scan_date
        assert not mock_update.called

        # 5. Force run (force=True) -> Re-executes workflow incrementally
        summary3 = run_daily_scan_workflow(force=True, db_path=test_db)
        assert summary3 is not None
        assert mock_update.called


def test_daily_scan_failed_run_recorded(tmp_path):
    test_db = tmp_path / "test_swinglens_fail.db"
    init_db(test_db)

    with patch("backend.scanner.daily_workflow.run_market_data_update", side_effect=ValueError("Simulated update failure")):
        try:
            run_daily_scan_workflow(force=True, db_path=test_db)
        except ValueError as err:
            assert "Simulated update failure" in str(err)

    status = get_daily_scan_status(db_path=test_db)
    assert status["already_completed"] is False
    assert status["status"] == "FAILED"
    assert "Simulated update failure" in status["error_message"]


def test_api_daily_scan_endpoints():
    res_status = client.get("/api/daily-scan/status")
    assert res_status.status_code == 200

    with patch("backend.scanner.daily_workflow.run_market_data_update"):
        res_run = client.post("/api/daily-scan/run?force=false")
        assert res_run.status_code == 200
        assert "scan_date" in res_run.json()
