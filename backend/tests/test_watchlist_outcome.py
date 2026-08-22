from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.database.connection import get_db_connection, init_db
from backend.watchlist import WatchlistOutcome, WatchlistOutcomeService, WatchlistService, WatchlistSetupCreate


def setup_data(**changes):
    data = dict(symbol="OUTCOME", signal_date="2026-01-10", aggregated_score=3, signal_strength="MODERATE",
                buy_strategies=["EMA Pullback"], entry_price=100, stop_loss=90, target_price=120,
                risk_reward=2, best_strategy_name="EMA Pullback")
    data.update(changes)
    return data


@pytest.fixture
def outcome_env(tmp_path):
    path = tmp_path / "outcome.db"
    init_db(path)
    conn = get_db_connection(path)
    conn.execute("INSERT INTO stocks (symbol, ticker) VALUES ('OUTCOME', 'OUTCOME')")
    conn.commit()
    conn.close()
    watchlist = WatchlistService(path)

    def create(**changes):
        return watchlist.create(WatchlistSetupCreate(**setup_data(**changes)))

    def candles(items):
        conn = get_db_connection(path)
        stock_id = conn.execute("SELECT id FROM stocks WHERE symbol = 'OUTCOME'").fetchone()["id"]
        conn.executemany("""INSERT INTO daily_prices (stock_id, trade_date, open, high, low, close, volume)
                          VALUES (?, ?, ?, ?, ?, ?, ?)""",
                         [(stock_id, day, low, high, low, high, 1) for day, high, low in items])
        conn.commit()
        conn.close()

    return path, create, candles


def test_pending_without_future_candles(outcome_env):
    path, create, _ = outcome_env
    result = WatchlistOutcomeService(path).evaluate(create().id)
    assert result.outcome == WatchlistOutcome.PENDING
    assert result.entry_date is None


def test_entry_reached_and_excursions(outcome_env):
    path, create, candles = outcome_env
    setup = create()
    candles([("2026-01-11", 108, 95), ("2026-01-12", 115, 92)])
    result = WatchlistOutcomeService(path).evaluate(setup.id)
    assert result.outcome == WatchlistOutcome.ENTRY_REACHED
    assert result.entry_date == date(2026, 1, 11)
    assert result.mfe == 15 and result.mfe_r == 1.5
    assert result.mae == 8 and result.mae_r == 0.8
    assert result.holding_days is None and result.realized_r is None


def test_no_entry_expires_after_configured_sessions(outcome_env):
    path, create, candles = outcome_env
    setup = create()
    candles([("2026-01-11", 95, 91), ("2026-01-12", 99, 91)])
    assert WatchlistOutcomeService(path, max_holding_days=2).evaluate(setup.id).outcome == WatchlistOutcome.NO_ENTRY


@pytest.mark.parametrize("candle, expected, exit_price, realized", [
    (("2026-01-12", 121, 95), WatchlistOutcome.TARGET_HIT, 120, 2),
    (("2026-01-12", 110, 89), WatchlistOutcome.STOP_HIT, 90, -1),
])
def test_resolved_outcomes_and_r_multiple(outcome_env, candle, expected, exit_price, realized):
    path, create, candles = outcome_env
    setup = create()
    candles([("2026-01-11", 110, 95), candle])
    result = WatchlistOutcomeService(path).evaluate(setup.id)
    assert result.outcome == expected
    assert result.exit_price == exit_price and result.realized_r == realized
    assert result.holding_days == 1


@pytest.mark.parametrize("items", [
    [("2026-01-11", 121, 89)],
    [("2026-01-11", 121, 95)],
    [("2026-01-11", 110, 89)],
])
def test_daily_ohlc_ambiguity_on_entry_or_dual_touch(outcome_env, items):
    path, create, candles = outcome_env
    setup = create()
    candles(items)
    result = WatchlistOutcomeService(path).evaluate(setup.id)
    assert result.outcome == WatchlistOutcome.AMBIGUOUS
    assert result.realized_r is None and result.holding_days == 0


def test_later_dual_touch_is_ambiguous(outcome_env):
    path, create, candles = outcome_env
    setup = create()
    candles([("2026-01-11", 110, 95), ("2026-01-12", 121, 89)])
    assert WatchlistOutcomeService(path).evaluate(setup.id).outcome == WatchlistOutcome.AMBIGUOUS


def test_expiration_after_entry_uses_trading_day_count(outcome_env):
    path, create, candles = outcome_env
    setup = create()
    candles([("2026-01-11", 110, 95), ("2026-01-12", 111, 95), ("2026-01-13", 112, 95)])
    result = WatchlistOutcomeService(path, max_holding_days=2).evaluate(setup.id)
    assert result.outcome == WatchlistOutcome.EXPIRED
    assert result.holding_days == 2 and result.exit_date == date(2026, 1, 13)


def test_signal_date_and_prior_candles_are_excluded(outcome_env):
    path, create, candles = outcome_env
    setup = create()
    candles([("2026-01-09", 130, 80), ("2026-01-10", 130, 80), ("2026-01-11", 99, 95)])
    result = WatchlistOutcomeService(path).evaluate(setup.id)
    assert result.outcome == WatchlistOutcome.PENDING


def test_repeated_evaluation_is_deterministic_and_final_is_immutable(outcome_env):
    path, create, candles = outcome_env
    setup = create()
    candles([("2026-01-11", 110, 95), ("2026-01-12", 121, 95)])
    service = WatchlistOutcomeService(path)
    first = service.evaluate(setup.id)
    candles([("2026-01-13", 130, 80)])
    second = service.evaluate(setup.id)
    assert first.model_dump() == second.model_dump()


def test_repeated_unresolved_evaluation_is_deterministic(outcome_env):
    path, create, _ = outcome_env
    service = WatchlistOutcomeService(path)
    first = service.evaluate(create().id)
    second = service.evaluate(first.id)
    assert first.model_dump() == second.model_dump()


def test_evaluation_api(monkeypatch, outcome_env):
    path, create, candles = outcome_env
    setup = create()
    candles([("2026-01-11", 110, 95), ("2026-01-12", 121, 95)])
    monkeypatch.setattr("backend.app.main.WatchlistOutcomeService", lambda: WatchlistOutcomeService(path))
    response = TestClient(app).post(f"/api/watchlist/{setup.id}/evaluate")
    assert response.status_code == 200
    assert response.json()["outcome"] == "TARGET_HIT"
