"""
Unit tests for Strategy Historical Quality Analytics.

Tests cover:
- Dynamic strategy discovery from StrategyRegistry
- Metric calculations (trades, wins, losses, win_rate, total_r, avg_r, profit_factor,
  target_hit_rate, stop_hit_rate, ambiguous_rate, MFE/MAE excursions)
- Deterministic classification logic (POSITIVE, NEGATIVE, NEUTRAL, INSUFFICIENT_DATA)
- Date and symbol filtering
- Insufficient data handling (< 10 trades)
- Unknown strategy error handling (404)
- Determinism
- Strict look-ahead protection
- FastAPI endpoints for analytics
"""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.analytics import (
    StrategyAnalyticsResponse,
    StrategyAnalyticsService,
    StrategyQualityClassification,
    StrategyQualityMetrics,
    classify_strategy,
)
from backend.app.main import app
from backend.strategies.base import BaseStrategy
from backend.strategies.models import SignalType, StrategySignal
from backend.strategies.registry import list_strategies


# ---------------------------------------------------------------------------
# Helpers & Mock Strategies
# ---------------------------------------------------------------------------

def create_synthetic_candles(count: int = 150, start_price: float = 100.0) -> pd.DataFrame:
    """Generates synthetic daily OHLCV candles."""
    dates = pd.date_range("2023-01-01", periods=count, freq="B").strftime("%Y-%m-%d").tolist()
    data = []
    price = start_price
    for i, d in enumerate(dates):
        o = price
        h = price + 2.0
        l = price - 2.0
        c = price + 0.5
        v = 100000 + i * 50
        data.append({"trade_date": d, "open": o, "high": h, "low": l, "close": c, "volume": v})
        price = c
    return pd.DataFrame(data)


class MockPositiveStrategy(BaseStrategy):
    name = "Mock Positive Strategy"
    version = "1.0.0"

    def generate_signals(self, df: pd.DataFrame) -> list[StrategySignal]:
        signals = []
        sym = df["symbol"].iloc[0] if "symbol" in df.columns else "TEST"
        # Generate 12 winning trades (BUY every 10 candles with TP that gets hit)
        for i in range(len(df)):
            dt = df["trade_date"].iloc[i]
            if i % 10 == 0 and i < 120:
                p = float(df["close"].iloc[i])
                signals.append(
                    StrategySignal(
                        symbol=sym,
                        strategy_name=self.name,
                        strategy_version=self.version,
                        signal=SignalType.BUY,
                        signal_date=dt,
                        entry_price=p,
                        stop_loss=p - 5.0,
                        target_price=p + 1.0,  # Easy target hit next candle
                    )
                )
            else:
                signals.append(
                    StrategySignal(
                        symbol=sym,
                        strategy_name=self.name,
                        strategy_version=self.version,
                        signal=SignalType.HOLD,
                        signal_date=dt,
                    )
                )
        return signals


class MockNegativeStrategy(BaseStrategy):
    name = "Mock Negative Strategy"
    version = "1.0.0"

    def generate_signals(self, df: pd.DataFrame) -> list[StrategySignal]:
        signals = []
        sym = df["symbol"].iloc[0] if "symbol" in df.columns else "TEST"
        # Generate 12 losing trades (BUY with tight stop loss that gets hit)
        for i in range(len(df)):
            dt = df["trade_date"].iloc[i]
            if i % 10 == 0 and i < 120:
                p = float(df["close"].iloc[i])
                signals.append(
                    StrategySignal(
                        symbol=sym,
                        strategy_name=self.name,
                        strategy_version=self.version,
                        signal=SignalType.BUY,
                        signal_date=dt,
                        entry_price=p,
                        stop_loss=p - 0.1,  # Stop loss hit immediately
                        target_price=p + 20.0,
                    )
                )
            else:
                signals.append(
                    StrategySignal(
                        symbol=sym,
                        strategy_name=self.name,
                        strategy_version=self.version,
                        signal=SignalType.HOLD,
                        signal_date=dt,
                    )
                )
        return signals


class MockFewTradesStrategy(BaseStrategy):
    name = "Mock Few Trades Strategy"
    version = "1.0.0"

    def generate_signals(self, df: pd.DataFrame) -> list[StrategySignal]:
        signals = []
        sym = df["symbol"].iloc[0] if "symbol" in df.columns else "TEST"
        # Only 2 trades generated
        for i in range(len(df)):
            dt = df["trade_date"].iloc[i]
            if i in (0, 30):
                p = float(df["close"].iloc[i])
                signals.append(
                    StrategySignal(
                        symbol=sym,
                        strategy_name=self.name,
                        strategy_version=self.version,
                        signal=SignalType.BUY,
                        signal_date=dt,
                        entry_price=p,
                        stop_loss=p - 5.0,
                        target_price=p + 5.0,
                    )
                )
            else:
                signals.append(
                    StrategySignal(
                        symbol=sym,
                        strategy_name=self.name,
                        strategy_version=self.version,
                        signal=SignalType.HOLD,
                        signal_date=dt,
                    )
                )
        return signals


# ---------------------------------------------------------------------------
# 1. Dynamic Discovery Test
# ---------------------------------------------------------------------------

def test_dynamic_strategy_discovery():
    """All 5 production strategies are discovered in the registry."""
    registered = [s["name"] for s in list_strategies()]
    expected_strategies = [
        "EMA Pullback",
        "MA Trend Breakout",
        "RSI Mean-Reversion",
        "MACD Momentum",
        "Bollinger Squeeze",
    ]
    for exp in expected_strategies:
        assert exp in registered


# ---------------------------------------------------------------------------
# 2. Classification Thresholds Unit Tests
# ---------------------------------------------------------------------------

def test_classification_thresholds():
    # Insufficient data
    c, r = classify_strategy(trades=8, total_r=5.0, profit_factor=1.5, average_r=0.6, min_trades=10)
    assert c == StrategyQualityClassification.INSUFFICIENT_DATA

    # Positive
    c, r = classify_strategy(trades=15, total_r=8.5, profit_factor=1.4, average_r=0.57, min_trades=10)
    assert c == StrategyQualityClassification.POSITIVE

    # Negative
    c, r = classify_strategy(trades=15, total_r=-10.2, profit_factor=0.6, average_r=-0.68, min_trades=10)
    assert c == StrategyQualityClassification.NEGATIVE

    # Neutral (mixed metrics: positive total_r but profit_factor < 1.0)
    c, r = classify_strategy(trades=15, total_r=1.0, profit_factor=0.9, average_r=0.07, min_trades=10)
    assert c == StrategyQualityClassification.NEUTRAL


# ---------------------------------------------------------------------------
# 3. Analytics Service Metric Calculations
# ---------------------------------------------------------------------------

def test_evaluate_positive_strategy_metrics():
    df = create_synthetic_candles(150)
    df["symbol"] = "TESTSYM"
    stock_data = {"TESTSYM": df}

    service = StrategyAnalyticsService()
    strat = MockPositiveStrategy()
    metrics = service.evaluate_strategy_on_data(strat, stock_data)

    assert metrics.strategy_name == "Mock Positive Strategy"
    assert metrics.trades >= 10
    assert metrics.wins > 0
    assert metrics.win_rate > 0.0
    assert metrics.classification == StrategyQualityClassification.POSITIVE
    assert metrics.target_hit_rate > 0.0
    assert metrics.average_mfe_r >= 0.0
    assert metrics.average_mae_r >= 0.0
    assert metrics.per_stock is not None
    assert "TESTSYM" in metrics.per_stock


def test_evaluate_negative_strategy_metrics():
    df = create_synthetic_candles(150)
    df["symbol"] = "TESTSYM"
    stock_data = {"TESTSYM": df}

    service = StrategyAnalyticsService()
    strat = MockNegativeStrategy()
    metrics = service.evaluate_strategy_on_data(strat, stock_data)

    assert metrics.strategy_name == "Mock Negative Strategy"
    assert metrics.trades >= 10
    assert metrics.losses > 0
    assert metrics.classification == StrategyQualityClassification.NEGATIVE
    assert metrics.stop_hit_rate > 0.0


def test_evaluate_insufficient_data_strategy():
    df = create_synthetic_candles(150)
    df["symbol"] = "TESTSYM"
    stock_data = {"TESTSYM": df}

    service = StrategyAnalyticsService()
    strat = MockFewTradesStrategy()
    metrics = service.evaluate_strategy_on_data(strat, stock_data)

    assert metrics.trades == 2
    assert metrics.classification == StrategyQualityClassification.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# 4. Deterministic Output
# ---------------------------------------------------------------------------

def test_analytics_determinism():
    df = create_synthetic_candles(150)
    df["symbol"] = "TESTSYM"
    stock_data = {"TESTSYM": df}

    service = StrategyAnalyticsService()
    strat = MockPositiveStrategy()
    res1 = service.evaluate_strategy_on_data(strat, stock_data)
    res2 = service.evaluate_strategy_on_data(strat, stock_data)

    assert res1.trades == res2.trades
    assert res1.total_r == res2.total_r
    assert res1.win_rate == res2.win_rate
    assert res1.profit_factor == res2.profit_factor
    assert res1.classification == res2.classification


# ---------------------------------------------------------------------------
# 5. Look-ahead bias protection
# ---------------------------------------------------------------------------

def test_lookahead_protection():
    """Altering future price data after a trade exit does not change the trade outcome."""
    df1 = create_synthetic_candles(150)
    df1["symbol"] = "TESTSYM"

    df2 = df1.copy()
    # Mutate the last 20 candles (future after the mock signals)
    df2.loc[130:, "close"] = df2.loc[130:, "close"] * 2.0

    service = StrategyAnalyticsService()
    strat = MockPositiveStrategy()
    res1 = service.evaluate_strategy_on_data(strat, {"TESTSYM": df1})
    res2 = service.evaluate_strategy_on_data(strat, {"TESTSYM": df2})

    # The trades generated up to candle 120 must be identical in both runs
    assert res1.trades == res2.trades
    assert res1.total_r == res2.total_r
    assert res1.win_rate == res2.win_rate


# ---------------------------------------------------------------------------
# 6. FastAPI Endpoints Integration Tests
# ---------------------------------------------------------------------------

def test_api_get_all_strategies_analytics():
    client = TestClient(app)
    # Run with small symbol subset for fast testing
    response = client.get("/api/analytics/strategies?symbols=BANKBARODA,CHOLAFIN")
    assert response.status_code == 200
    data = response.json()
    assert "strategies" in data
    assert "symbols" in data
    assert len(data["strategies"]) >= 5
    strategy_names = [s["strategy_name"] for s in data["strategies"]]
    assert "EMA Pullback" in strategy_names
    assert "MACD Momentum" in strategy_names


def test_api_get_single_strategy_analytics():
    client = TestClient(app)
    response = client.get("/api/analytics/strategies/ema_pullback?symbols=BANKBARODA")
    assert response.status_code == 200
    data = response.json()
    assert data["strategy_name"] == "EMA Pullback"
    assert "trades" in data
    assert "win_rate" in data
    assert "total_r" in data
    assert "classification" in data
    assert "target_hit_rate" in data
    assert "stop_hit_rate" in data
    assert "average_mfe_r" in data
    assert "average_mae_r" in data


def test_api_get_unknown_strategy_analytics():
    client = TestClient(app)
    response = client.get("/api/analytics/strategies/unknown_nonexistent_strategy")
    assert response.status_code == 404
    data = response.json()
    assert "Unknown strategy" in data["detail"]


def test_api_date_filtering():
    client = TestClient(app)
    response = client.get(
        "/api/analytics/strategies/ema_pullback?symbols=BANKBARODA&start_date=2024-01-01&end_date=2024-12-31"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy_name"] == "EMA Pullback"
    assert "trades" in data
