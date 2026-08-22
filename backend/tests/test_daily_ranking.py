"""
Unit tests for the Daily Signal Ranking layer (DailySignalRanker, RankedSignal,
DailySignalRanking, SignalTier).

All tests use monkeypatching and synthetic data — no real SQLite calls.
"""
import pytest
from typing import List, Optional
from unittest.mock import MagicMock, patch

from backend.aggregator.models import (
    AggregatedSignalResult,
    AggregatedSignalStrength,
    StrategyVote,
)
from backend.ranking.models import (
    DailySignalRanking,
    RankedSignal,
    SignalTier,
    strength_to_tier,
)
from backend.ranking.ranker import DailySignalRanker, _rank_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agg_result(
    symbol: str,
    score: int,
    buy_count: int,
    best_rr: Optional[float] = None,
    strength: Optional[AggregatedSignalStrength] = None,
    signal_date: str = "2024-08-22",
) -> AggregatedSignalResult:
    """Creates a minimal AggregatedSignalResult for testing."""
    if strength is None:
        from backend.aggregator.models import score_to_strength
        strength = score_to_strength(score)

    hold_count = 5 - buy_count
    return AggregatedSignalResult(
        symbol=symbol,
        signal_date=signal_date,
        strategies_evaluated=5,
        strategies_total=5,
        buy_count=buy_count,
        hold_count=hold_count,
        score=score,
        strength=strength,
        buy_strategies=[f"S{i}" for i in range(buy_count)],
        hold_strategies=[f"H{i}" for i in range(hold_count)],
        error_strategies=[],
        best_entry_price=100.0 if buy_count > 0 else None,
        best_stop_loss=95.0 if buy_count > 0 else None,
        best_target_price=110.0 if buy_count > 0 else None,
        best_risk_reward=best_rr,
        best_strategy_name="S0" if buy_count > 0 else None,
        votes=[],
    )


def _make_ranker_with_mock_results(
    agg_results: List[AggregatedSignalResult],
    universe: Optional[List[dict]] = None,
) -> DailySignalRanker:
    """
    Returns a DailySignalRanker whose run() is patched so that
    get_active_universe_constituents and SignalAggregator.aggregate are mocked.
    """
    return DailySignalRanker()


def _run_with_mocks(
    agg_results: List[AggregatedSignalResult],
    universe: Optional[List[dict]] = None,
    limit: Optional[int] = None,
) -> DailySignalRanking:
    """
    Patches the two external dependencies of DailySignalRanker.run()
    and returns the resulting DailySignalRanking.
    """
    if universe is None:
        universe = [{"symbol": r.symbol, "company_name": None} for r in agg_results]

    symbol_to_result = {r.symbol: r for r in agg_results}

    import pandas as pd

    def mock_get_price_history(conn, symbol, end_date=None):
        # Return a minimal non-empty DataFrame
        return pd.DataFrame({
            "symbol": [symbol] * 250,
            "trade_date": [f"2024-{str(i % 12 + 1).zfill(2)}-01" for i in range(250)],
            "open": [100.0] * 250,
            "high": [102.0] * 250,
            "low": [98.0] * 250,
            "close": [100.0] * 250,
            "volume": [10000] * 250,
        })

    def mock_aggregate(self, symbol, df, strategy_keys=None):
        return symbol_to_result[symbol]

    with patch(
        "backend.ranking.ranker.get_active_universe_constituents",
        return_value=universe,
    ), patch(
        "backend.ranking.ranker.get_price_history",
        side_effect=mock_get_price_history,
    ), patch(
        "backend.ranking.ranker.get_db_connection",
        return_value=MagicMock(),
    ), patch(
        "backend.aggregator.aggregator.SignalAggregator.aggregate",
        new=mock_aggregate,
    ):
        ranker = DailySignalRanker()
        return ranker.run(limit=limit)


# ---------------------------------------------------------------------------
# Test 1 — Rank 5 mock stocks by score (descending)
# ---------------------------------------------------------------------------

def test_rank_by_score_descending():
    """Stocks with higher score rank higher."""
    results = [
        _make_agg_result("ALPHA", score=1, buy_count=1),
        _make_agg_result("BETA", score=5, buy_count=5),
        _make_agg_result("GAMMA", score=3, buy_count=3),
        _make_agg_result("DELTA", score=0, buy_count=0),
        _make_agg_result("EPSILON", score=4, buy_count=4),
    ]
    ranking = _run_with_mocks(results)

    symbols = [r.symbol for r in ranking.results]
    assert symbols == ["BETA", "EPSILON", "GAMMA", "ALPHA", "DELTA"]
    assert ranking.results[0].rank == 1
    assert ranking.results[4].rank == 5


# ---------------------------------------------------------------------------
# Test 2 — Equal score: BUY count is tie-breaker (descending)
# ---------------------------------------------------------------------------

def test_tiebreak_by_buy_count():
    """Equal score breaks tie on buy_count descending."""
    # Two stocks both score=3 but different buy_count
    results = [
        _make_agg_result("ZETA", score=3, buy_count=3),
        _make_agg_result("ETA", score=3, buy_count=2),  # lower buy_count → lower rank
    ]
    ranking = _run_with_mocks(results)

    assert ranking.results[0].symbol == "ZETA"
    assert ranking.results[1].symbol == "ETA"


# ---------------------------------------------------------------------------
# Test 3 — Equal score & BUY count: RR is tie-breaker (descending)
# ---------------------------------------------------------------------------

def test_tiebreak_by_risk_reward():
    """Equal score and buy_count breaks tie on best_risk_reward descending."""
    results = [
        _make_agg_result("THETA", score=3, buy_count=3, best_rr=1.5),
        _make_agg_result("IOTA", score=3, buy_count=3, best_rr=3.0),  # higher RR wins
    ]
    ranking = _run_with_mocks(results)

    assert ranking.results[0].symbol == "IOTA"
    assert ranking.results[1].symbol == "THETA"


# ---------------------------------------------------------------------------
# Test 4 — Final tie-breaker is alphabetical symbol ordering
# ---------------------------------------------------------------------------

def test_tiebreak_by_symbol_alphabetical():
    """When score, buy_count, and RR are all equal, symbols sort alphabetically."""
    results = [
        _make_agg_result("ZYMBOL", score=2, buy_count=2, best_rr=2.0),
        _make_agg_result("ALPHA", score=2, buy_count=2, best_rr=2.0),
        _make_agg_result("MANGO", score=2, buy_count=2, best_rr=2.0),
    ]
    ranking = _run_with_mocks(results)

    symbols = [r.symbol for r in ranking.results]
    assert symbols == ["ALPHA", "MANGO", "ZYMBOL"]


# ---------------------------------------------------------------------------
# Test 5 — Top-N limit works
# ---------------------------------------------------------------------------

def test_limit_shortlist():
    """Shortlist contains exactly limit items; results contains all evaluated."""
    results = [
        _make_agg_result("A", score=5, buy_count=5),
        _make_agg_result("B", score=4, buy_count=4),
        _make_agg_result("C", score=3, buy_count=3),
        _make_agg_result("D", score=2, buy_count=2),
        _make_agg_result("E", score=1, buy_count=1),
    ]
    ranking = _run_with_mocks(results, limit=3)

    assert len(ranking.shortlist) == 3
    assert len(ranking.results) == 5
    assert ranking.shortlist[0].symbol == "A"
    assert ranking.shortlist[2].symbol == "C"


# ---------------------------------------------------------------------------
# Test 6 — Invalid limit is rejected (API layer)
# ---------------------------------------------------------------------------

def test_invalid_limit_rejected():
    """The FastAPI endpoint raises 422 for out-of-range limit values."""
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    response = client.get("/api/daily-signals?limit=0")
    assert response.status_code == 422

    response = client.get("/api/daily-signals?limit=201")
    assert response.status_code == 422

    response = client.get("/api/daily-signals?limit=-5")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 7 — NO_SIGNAL stocks are included (not excluded)
# ---------------------------------------------------------------------------

def test_no_signal_stocks_included_in_results():
    """Stocks with score=0 (NO_SIGNAL) are still ranked (at the bottom)."""
    results = [
        _make_agg_result("A", score=3, buy_count=3),
        _make_agg_result("B", score=0, buy_count=0),
    ]
    ranking = _run_with_mocks(results)

    assert ranking.evaluated_count == 2
    symbols = [r.symbol for r in ranking.results]
    assert "B" in symbols
    assert ranking.results[-1].symbol == "B"
    assert ranking.results[-1].tier == SignalTier.WEAK_OR_NO_SIGNAL


# ---------------------------------------------------------------------------
# Test 8 — Signal tier classification
# ---------------------------------------------------------------------------

def test_tier_classifications():
    """strength_to_tier maps strength correctly to tiers."""
    assert strength_to_tier(AggregatedSignalStrength.VERY_STRONG) == SignalTier.STRONG_OPPORTUNITY
    assert strength_to_tier(AggregatedSignalStrength.STRONG) == SignalTier.STRONG_OPPORTUNITY
    assert strength_to_tier(AggregatedSignalStrength.MODERATE) == SignalTier.MODERATE_OPPORTUNITY
    assert strength_to_tier(AggregatedSignalStrength.WEAK) == SignalTier.WEAK_OR_NO_SIGNAL
    assert strength_to_tier(AggregatedSignalStrength.NO_SIGNAL) == SignalTier.WEAK_OR_NO_SIGNAL


def test_ranked_signal_tier_field():
    """RankedSignal.tier is correctly populated from strength."""
    results = [
        _make_agg_result("A", score=5, buy_count=5),  # VERY_STRONG
        _make_agg_result("B", score=3, buy_count=3),  # MODERATE
        _make_agg_result("C", score=0, buy_count=0),  # NO_SIGNAL
    ]
    ranking = _run_with_mocks(results)

    by_symbol = {r.symbol: r for r in ranking.results}
    assert by_symbol["A"].tier == SignalTier.STRONG_OPPORTUNITY
    assert by_symbol["B"].tier == SignalTier.MODERATE_OPPORTUNITY
    assert by_symbol["C"].tier == SignalTier.WEAK_OR_NO_SIGNAL


# ---------------------------------------------------------------------------
# Test 9 — One failed stock does NOT fail the entire ranking
# ---------------------------------------------------------------------------

def test_one_failed_stock_does_not_abort_ranking():
    """If get_price_history raises for one stock, others are still ranked."""
    universe = [
        {"symbol": "GOOD1", "company_name": "Good Corp 1"},
        {"symbol": "BADSTOCK", "company_name": "Bad Corp"},
        {"symbol": "GOOD2", "company_name": "Good Corp 2"},
    ]
    good_result = {
        "GOOD1": _make_agg_result("GOOD1", score=3, buy_count=3),
        "GOOD2": _make_agg_result("GOOD2", score=2, buy_count=2),
    }

    import pandas as pd

    def mock_get_price_history(conn, symbol, end_date=None):
        if symbol == "BADSTOCK":
            raise RuntimeError("Simulated DB error")
        return pd.DataFrame({
            "symbol": [symbol] * 250,
            "trade_date": [f"2024-01-{str(i % 28 + 1).zfill(2)}" for i in range(250)],
            "open": [100.0] * 250,
            "high": [102.0] * 250,
            "low": [98.0] * 250,
            "close": [100.0] * 250,
            "volume": [10000] * 250,
        })

    def mock_aggregate(self, symbol, df, strategy_keys=None):
        return good_result[symbol]

    with patch("backend.ranking.ranker.get_active_universe_constituents", return_value=universe), \
         patch("backend.ranking.ranker.get_price_history", side_effect=mock_get_price_history), \
         patch("backend.ranking.ranker.get_db_connection", return_value=MagicMock()), \
         patch("backend.aggregator.aggregator.SignalAggregator.aggregate", new=mock_aggregate):
        ranker = DailySignalRanker()
        ranking = ranker.run()

    assert ranking.evaluated_count == 2
    assert ranking.excluded_count == 1
    symbols = {r.symbol for r in ranking.results}
    assert symbols == {"GOOD1", "GOOD2"}
    assert "BADSTOCK" not in symbols


# ---------------------------------------------------------------------------
# Test 10 — Universe is obtained dynamically (not hardcoded)
# ---------------------------------------------------------------------------

def test_universe_is_dynamic():
    """The ranker calls get_active_universe_constituents, never a hardcoded list."""
    custom_universe = [
        {"symbol": "CUSTOM1", "company_name": "Custom Corp 1"},
        {"symbol": "CUSTOM2", "company_name": "Custom Corp 2"},
    ]
    results_map = {
        "CUSTOM1": _make_agg_result("CUSTOM1", score=1, buy_count=1),
        "CUSTOM2": _make_agg_result("CUSTOM2", score=2, buy_count=2),
    }

    import pandas as pd

    def mock_get_price_history(conn, symbol, end_date=None):
        return pd.DataFrame({
            "symbol": [symbol] * 250,
            "trade_date": [f"2024-01-{str(i % 28 + 1).zfill(2)}" for i in range(250)],
            "open": [100.0] * 250,
            "high": [102.0] * 250,
            "low": [98.0] * 250,
            "close": [100.0] * 250,
            "volume": [10000] * 250,
        })

    def mock_aggregate(self, symbol, df, strategy_keys=None):
        return results_map[symbol]

    with patch("backend.ranking.ranker.get_active_universe_constituents", return_value=custom_universe) as mock_gau, \
         patch("backend.ranking.ranker.get_price_history", side_effect=mock_get_price_history), \
         patch("backend.ranking.ranker.get_db_connection", return_value=MagicMock()), \
         patch("backend.aggregator.aggregator.SignalAggregator.aggregate", new=mock_aggregate):
        ranker = DailySignalRanker()
        ranking = ranker.run()

    # Verify the universe function was called (not a hardcoded list)
    mock_gau.assert_called_once()
    assert ranking.universe_size == 2
    symbols = {r.symbol for r in ranking.results}
    assert symbols == {"CUSTOM1", "CUSTOM2"}


# ---------------------------------------------------------------------------
# Test 11 — Empty universe is handled safely
# ---------------------------------------------------------------------------

def test_empty_universe_handled_safely():
    """When the universe has no constituents, ranking returns cleanly with zero results."""
    with patch("backend.ranking.ranker.get_active_universe_constituents", return_value=[]), \
         patch("backend.ranking.ranker.get_db_connection", return_value=MagicMock()):
        ranker = DailySignalRanker()
        ranking = ranker.run()

    assert ranking.universe_size == 0
    assert ranking.evaluated_count == 0
    assert ranking.excluded_count == 0
    assert ranking.buy_signal_count == 0
    assert ranking.results == []
    assert ranking.shortlist == []


# ---------------------------------------------------------------------------
# Test 12 — Results are deterministic (same input → same output)
# ---------------------------------------------------------------------------

def test_results_are_deterministic():
    """Running the ranker twice on the same mocked data produces identical output."""
    results = [
        _make_agg_result("ALPHA", score=3, buy_count=3, best_rr=2.0),
        _make_agg_result("BETA", score=3, buy_count=3, best_rr=1.5),
        _make_agg_result("GAMMA", score=2, buy_count=2, best_rr=None),
    ]
    r1 = _run_with_mocks(results)
    r2 = _run_with_mocks(results)

    assert [x.symbol for x in r1.results] == [x.symbol for x in r2.results]
    assert [x.rank for x in r1.results] == [x.rank for x in r2.results]
    assert [x.score for x in r1.results] == [x.score for x in r2.results]


# ---------------------------------------------------------------------------
# Test 13 — Existing aggregator endpoint is unaffected
# ---------------------------------------------------------------------------

def test_existing_aggregator_endpoint_still_works(monkeypatch):
    """GET /api/aggregator/{symbol} must still return AggregatedSignalResult."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.aggregator.models import AggregatedSignalStrength

    dummy_result = _make_agg_result("BANKBARODA", score=0, buy_count=0)

    def mock_aggregate_for_symbol(self, symbol, **kwargs):
        return dummy_result

    monkeypatch.setattr(
        "backend.aggregator.aggregator.SignalAggregator.aggregate_for_symbol",
        mock_aggregate_for_symbol,
    )

    client = TestClient(app)
    response = client.get("/api/aggregator/BANKBARODA")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BANKBARODA"
    assert "score" in data
    assert "strength" in data
    assert "votes" in data


# ---------------------------------------------------------------------------
# Test 14 — _rank_key ordering (unit test for the sort key function)
# ---------------------------------------------------------------------------

def test_rank_key_ordering():
    """_rank_key produces consistent ordering matching documented priority."""
    r_high = _make_agg_result("Z", score=5, buy_count=5, best_rr=3.0)
    r_mid = _make_agg_result("A", score=3, buy_count=3, best_rr=1.0)
    r_low = _make_agg_result("B", score=1, buy_count=1, best_rr=None)

    # Lower sort key = better rank
    assert _rank_key(r_high) < _rank_key(r_mid) < _rank_key(r_low)


# ---------------------------------------------------------------------------
# Test 15 — buy_signal_count counts stocks with at least 1 BUY
# ---------------------------------------------------------------------------

def test_buy_signal_count():
    """buy_signal_count equals the number of stocks with buy_count > 0."""
    results = [
        _make_agg_result("A", score=3, buy_count=3),
        _make_agg_result("B", score=0, buy_count=0),
        _make_agg_result("C", score=1, buy_count=1),
    ]
    ranking = _run_with_mocks(results)

    assert ranking.buy_signal_count == 2  # A and C have buy signals
