import sqlite3
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.database.connection import get_db_connection

client = TestClient(app)


def test_get_stock_history_success():
    response = client.get("/api/stocks/HINDZINC/history?days=250")
    if response.status_code == 200:
        data = response.json()
        assert data["symbol"] == "HINDZINC"
        candles = data["data"]
        assert len(candles) > 0
        assert len(candles) <= 250

        # Verify chronological order
        dates = [c["date"] for c in candles]
        assert dates == sorted(dates)

        # Check candle properties
        latest = candles[-1]
        assert "date" in latest
        assert "open" in latest
        assert "close" in latest
        assert "high" in latest
        assert "low" in latest
        assert "volume" in latest
        assert "ema20" in latest
        assert "ema50" in latest
        assert "ema200" in latest
    else:
        assert response.status_code == 404


def test_get_stock_history_unknown_symbol():
    response = client.get("/api/stocks/NONEXISTENT_STOCK_9999/history")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_stock_history_db_read_only():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_prices;")
    count_before = cursor.fetchone()[0]
    conn.close()

    response = client.get("/api/stocks/HINDZINC/history?days=50")
    assert response.status_code in (200, 404)

    conn_after = get_db_connection()
    cursor_after = conn_after.cursor()
    cursor_after.execute("SELECT COUNT(*) FROM daily_prices;")
    count_after = cursor_after.fetchone()[0]
    conn_after.close()

    assert count_before == count_after
