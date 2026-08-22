import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.database.connection import get_db_connection, init_db
from backend.watchlist import (
    DuplicateActiveSetupError, InvalidStatusTransitionError, WatchlistNotFoundError,
    WatchlistService, WatchlistSetupCreate, WatchlistStatus,
)


def payload(**overrides):
    values = dict(
        symbol="BANKBARODA", signal_date="2026-08-21", aggregated_score=4,
        signal_strength="STRONG", buy_strategies=["EMA Pullback", "MACD Momentum", "MA Breakout"],
        entry_price=500, stop_loss=480, target_price=560, risk_reward=3, best_strategy_name="EMA Pullback",
    )
    values.update(overrides)
    return values


@pytest.fixture
def service(tmp_path):
    db_path = tmp_path / "watchlist.db"
    init_db(db_path)
    conn = get_db_connection(db_path)
    conn.execute("INSERT INTO stocks (symbol, ticker, company_name) VALUES (?, ?, ?)",
                 ("BANKBARODA", "BANKBARODA", "Bank of Baroda"))
    conn.commit()
    conn.close()
    return WatchlistService(db_path)


def test_create_preserves_complete_signal_snapshot(service):
    created = service.create(WatchlistSetupCreate(**payload()))
    assert created.id == 1
    assert created.symbol == "BANKBARODA"
    assert created.company_name == "Bank of Baroda"
    assert created.status == WatchlistStatus.ACTIVE
    assert created.buy_strategies == ["EMA Pullback", "MACD Momentum", "MA Breakout"]
    assert created.entry_price == 500
    assert created.stop_loss == 480
    assert created.target_price == 560
    assert created.created_at is not None
    assert service.get(created.id).model_dump() == created.model_dump()


@pytest.mark.parametrize("changes", [
    {"signal_strength": "NO_SIGNAL"}, {"entry_price": 0}, {"stop_loss": 500},
    {"target_price": 500}, {"risk_reward": 0}, {"buy_strategies": ["EMA", "EMA"]},
])
def test_invalid_setup_snapshot_is_rejected(changes):
    with pytest.raises(ValidationError):
        WatchlistSetupCreate(**payload(**changes))


def test_list_defaults_to_active_and_filters_status(service):
    created = service.create(WatchlistSetupCreate(**payload()))
    service.update_status(created.id, WatchlistStatus.TRIGGERED)
    assert service.list() == []
    assert [item.id for item in service.list(WatchlistStatus.TRIGGERED)] == [created.id]


@pytest.mark.parametrize("status", [WatchlistStatus.TRIGGERED, WatchlistStatus.EXPIRED, WatchlistStatus.CANCELLED])
def test_valid_active_lifecycle_transitions(service, status):
    created = service.create(WatchlistSetupCreate(**payload()))
    assert service.update_status(created.id, status).status == status


def test_invalid_status_transitions_are_rejected(service):
    created = service.create(WatchlistSetupCreate(**payload()))
    with pytest.raises(InvalidStatusTransitionError):
        service.update_status(created.id, WatchlistStatus.ACTIVE)
    service.update_status(created.id, WatchlistStatus.TRIGGERED)
    with pytest.raises(InvalidStatusTransitionError):
        service.update_status(created.id, WatchlistStatus.CANCELLED)


def test_duplicate_active_setup_is_prevented_and_new_one_allowed_after_completion(service):
    first = service.create(WatchlistSetupCreate(**payload()))
    with pytest.raises(DuplicateActiveSetupError):
        service.create(WatchlistSetupCreate(**payload()))
    service.update_status(first.id, WatchlistStatus.TRIGGERED)
    assert service.create(WatchlistSetupCreate(**payload())).status == WatchlistStatus.ACTIVE


def test_database_partial_unique_constraint_exists(service):
    service.create(WatchlistSetupCreate(**payload()))
    conn = get_db_connection(service.db_path)
    stock_id = conn.execute("SELECT id FROM stocks WHERE symbol = 'BANKBARODA'").fetchone()["id"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("""INSERT INTO watchlist_setups
            (stock_id, signal_date, status, aggregated_score, signal_strength, buy_strategies,
             entry_price, stop_loss, target_price, risk_reward, best_strategy_name)
            VALUES (?, '2026-08-22', 'ACTIVE', 1, 'WEAK', '[\"EMA\"]', 100, 90, 120, 2, 'EMA')""", (stock_id,))
    conn.close()


def test_unknown_setup_and_stock_are_reported(service):
    with pytest.raises(WatchlistNotFoundError):
        service.get(999)
    with pytest.raises(WatchlistNotFoundError):
        service.create(WatchlistSetupCreate(**payload(symbol="MISSING")))


def test_api_create_list_get_and_update(monkeypatch, service):
    monkeypatch.setattr("backend.app.main.WatchlistService", lambda: service)
    client = TestClient(app)
    response = client.post("/api/watchlist", json=payload())
    assert response.status_code == 201
    created = response.json()
    setup_id = created["id"]
    assert client.get("/api/watchlist").json() == [created]
    assert client.get(f"/api/watchlist/{setup_id}").json() == created
    changed = client.patch(f"/api/watchlist/{setup_id}/status", json={"status": "TRIGGERED"})
    assert changed.status_code == 200
    assert changed.json()["status"] == "TRIGGERED"
    assert client.get("/api/watchlist").json() == []
    assert client.get("/api/watchlist?status=TRIGGERED").json()[0]["id"] == setup_id


def test_api_returns_deterministic_conflict_and_not_found(monkeypatch, service):
    monkeypatch.setattr("backend.app.main.WatchlistService", lambda: service)
    client = TestClient(app)
    assert client.post("/api/watchlist", json=payload()).status_code == 201
    assert client.post("/api/watchlist", json=payload()).status_code == 409
    assert client.get("/api/watchlist/999").status_code == 404
