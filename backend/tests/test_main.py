from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_backtest_single_stock_endpoint():
    response = client.get("/api/backtest/ABB")
    if response.status_code == 200:
        data = response.json()
        assert data["symbol"] == "ABB"
        assert "strategy_name" in data
        assert "win_rate" in data
        assert "profit_factor" in data
        assert "max_drawdown_percent" in data
        assert "average_holding_days" in data
        assert "maximum_holding_days" in data
        assert "average_r_multiple" in data
        assert "total_r" in data
        assert "trades" in data
    else:
        assert response.status_code in (404, 500)


def test_backtest_invalid_symbol_endpoint():
    response = client.get("/api/backtest/NONEXISTENT_STOCK_999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

