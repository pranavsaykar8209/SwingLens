import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.app.main import app
from backend.scanner import MarketScanner, ScanResult, ScanSignalType, ScanSummary

client = TestClient(app)


def test_1_health_endpoint_still_works():
    """1. Test that existing GET /health endpoint continues to function."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_2_get_latest_scan_success():
    """2. Test GET /api/scanner/latest returns HTTP 200 and expected schema."""
    response = client.get("/api/scanner/latest")
    assert response.status_code == 200
    data = response.json()

    # Check top-level schema keys
    required_keys = [
        "scan_date",
        "universe",
        "strategy",
        "strategy_version",
        "stocks_scanned",
        "buy_count",
        "watch_count",
        "hold_count",
        "skip_count",
        "results",
    ]
    for key in required_keys:
        assert key in data, f"Missing required key '{key}' in API response"


def test_3_correct_universe_returned():
    """3. Test that the requested universe is returned in the API response."""
    response = client.get("/api/scanner/latest?index=NIFTY_NEXT_50")
    assert response.status_code == 200
    assert response.json()["universe"] == "NIFTY_NEXT_50"


def test_4_correct_strategy_returned():
    """4. Test that the requested strategy is returned in the API response."""
    response = client.get("/api/scanner/latest?strategy=ema_pullback")
    assert response.status_code == 200
    data = response.json()
    assert "EMA Pullback" in data["strategy"]
    assert data["strategy_version"] == "1.0"


def test_5_results_contain_structured_scan_results():
    """5. Test that results list contains structured ScanResult objects."""
    response = client.get("/api/scanner/latest")
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert isinstance(results, list)
    assert len(results) > 0

    first_item = results[0]
    result_keys = ["symbol", "signal", "strategy_name", "strategy_version", "status"]
    for key in result_keys:
        assert key in first_item, f"Missing result key '{key}'"
    assert first_item["signal"] in ["BUY", "WATCH", "HOLD", "ERROR"]


def test_6_unknown_strategy_returns_http_400():
    """6. Test that requesting an unknown/unregistered strategy returns HTTP 400."""
    response = client.get("/api/scanner/latest?strategy=non_existent_strategy_xyz")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Unknown strategy" in detail


def test_7_database_or_scanner_failure_returns_http_500():
    """7. Test that severe database or engine failure returns clean HTTP 500 without stack traces."""
    with patch.object(MarketScanner, "scan_summary", side_effect=RuntimeError("Database failure simulated")):
        response = client.get("/api/scanner/latest")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to execute daily market scan" in data["detail"]
        # Ensure stack trace is not exposed
        assert "Traceback" not in data["detail"]
        assert "RuntimeError" not in data["detail"]


def test_8_api_does_not_modify_daily_prices():
    """8. Test API execution does not mutate daily_prices database table."""
    conn = sqlite3.connect("data/swinglens.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_prices;")
    count_before = cursor.fetchone()[0]
    conn.close()

    response = client.get("/api/scanner/latest")
    assert response.status_code == 200

    conn = sqlite3.connect("data/swinglens.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_prices;")
    count_after = cursor.fetchone()[0]
    conn.close()

    assert count_before == count_after


def test_9_api_operates_offline_without_downloading_data(monkeypatch):
    """9. Test API execution operates strictly offline without external network calls."""
    def raise_on_network_call(*args, **kwargs):
        pytest.fail("API attempt to invoke external network download!")

    monkeypatch.setattr("httpx.get", raise_on_network_call)

    response = client.get("/api/scanner/latest")
    assert response.status_code == 200
    assert response.json()["universe"] == "NIFTY_NEXT_50"
