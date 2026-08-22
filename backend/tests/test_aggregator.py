"""
Unit tests for the Multi-Strategy Signal Aggregator.

Tests use synthetic OHLCV price data and monkeypatching to ensure:
- No real SQLite calls are made
- Individual strategy behaviour is not modified
- Scoring thresholds are applied exactly as documented
- Edge cases (errors, partial failures) are handled gracefully
"""
import pandas as pd
import pytest
from typing import List, Optional

from backend.aggregator.aggregator import SignalAggregator, PRODUCTION_STRATEGY_KEYS
from backend.aggregator.models import AggregatedSignalStrength, score_to_strength


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_price_df(count: int = 300, start_price: float = 100.0) -> pd.DataFrame:
    """Creates a minimal synthetic OHLCV DataFrame sufficient for indicator warm-up."""
    dates = pd.date_range(start="2023-01-01", periods=count, freq="B")
    prices = [start_price + i * 0.3 for i in range(count)]
    return pd.DataFrame(
        {
            "trade_date": dates.strftime("%Y-%m-%d"),
            "symbol": "TESTSYM",
            "open":   [p - 0.5 for p in prices],
            "high":   [p + 1.0 for p in prices],
            "low":    [p - 1.0 for p in prices],
            "close":  prices,
            "volume": [100_000] * count,
        }
    )


def _make_mock_signal(signal_type: str, strategy_name: str = "Test", version: str = "1.0"):
    """Returns a StrategySignal-like object with the given signal type."""
    from backend.strategies.models import SignalType, StrategySignal
    return StrategySignal(
        symbol="TESTSYM",
        strategy_name=strategy_name,
        strategy_version=version,
        signal=SignalType(signal_type),
        signal_date="2024-08-22",
        entry_price=100.0 if signal_type == "BUY" else None,
        stop_loss=95.0 if signal_type == "BUY" else None,
        target_price=110.0 if signal_type == "BUY" else None,
    )


# ---------------------------------------------------------------------------
# Test 1 — score_to_strength thresholds
# ---------------------------------------------------------------------------

def test_score_to_strength_mapping():
    """All threshold boundaries map to the correct AggregatedSignalStrength label."""
    assert score_to_strength(0) == AggregatedSignalStrength.NO_SIGNAL
    assert score_to_strength(1) == AggregatedSignalStrength.NO_SIGNAL
    assert score_to_strength(2) == AggregatedSignalStrength.WEAK
    assert score_to_strength(3) == AggregatedSignalStrength.MODERATE
    assert score_to_strength(4) == AggregatedSignalStrength.STRONG
    assert score_to_strength(5) == AggregatedSignalStrength.VERY_STRONG
    # Above maximum also saturates to VERY_STRONG
    assert score_to_strength(6) == AggregatedSignalStrength.VERY_STRONG


# ---------------------------------------------------------------------------
# Test 2 — All strategies return HOLD → NO_SIGNAL
# ---------------------------------------------------------------------------

def test_all_hold_produces_no_signal(monkeypatch):
    """When every strategy returns HOLD, score=0 and strength=NO_SIGNAL."""
    agg = SignalAggregator()
    df = make_price_df()

    # Patch each strategy in the registry to return HOLD
    def mock_generate_latest_signal(self, df_):
        return _make_mock_signal("HOLD", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert result.score == 0
    assert result.strength == AggregatedSignalStrength.NO_SIGNAL
    assert result.buy_count == 0
    assert len(result.buy_strategies) == 0
    assert len(result.error_strategies) == 0


# ---------------------------------------------------------------------------
# Test 3 — 1 BUY → NO_SIGNAL
# ---------------------------------------------------------------------------

def test_one_buy_produces_no_signal(monkeypatch):
    """A single BUY (score=1) still maps to NO_SIGNAL."""
    agg = SignalAggregator()
    df = make_price_df()

    buy_key = "ema_pullback"
    buy_name = "EMA Pullback"

    def mock_generate_latest_signal(self, df_):
        if self.name == buy_name:
            return _make_mock_signal("BUY", self.name, self.version)
        return _make_mock_signal("HOLD", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert result.score == 1
    assert result.strength == AggregatedSignalStrength.NO_SIGNAL
    assert result.buy_count == 1
    assert buy_name in result.buy_strategies


# ---------------------------------------------------------------------------
# Test 4 — 2 BUYs → WEAK
# ---------------------------------------------------------------------------

def test_two_buys_produces_weak(monkeypatch):
    """Two BUY signals (score=2) maps to WEAK."""
    agg = SignalAggregator()
    df = make_price_df()
    buy_names = {"EMA Pullback", "MACD Momentum"}

    def mock_generate_latest_signal(self, df_):
        if self.name in buy_names:
            return _make_mock_signal("BUY", self.name, self.version)
        return _make_mock_signal("HOLD", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert result.score == 2
    assert result.strength == AggregatedSignalStrength.WEAK
    assert set(result.buy_strategies) == buy_names


# ---------------------------------------------------------------------------
# Test 5 — 3 BUYs → MODERATE
# ---------------------------------------------------------------------------

def test_three_buys_produces_moderate(monkeypatch):
    """Three BUY signals (score=3) maps to MODERATE."""
    agg = SignalAggregator()
    df = make_price_df()
    buy_names = {"EMA Pullback", "MACD Momentum", "Bollinger Squeeze"}

    def mock_generate_latest_signal(self, df_):
        if self.name in buy_names:
            return _make_mock_signal("BUY", self.name, self.version)
        return _make_mock_signal("HOLD", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert result.score == 3
    assert result.strength == AggregatedSignalStrength.MODERATE


# ---------------------------------------------------------------------------
# Test 6 — 4 BUYs → STRONG
# ---------------------------------------------------------------------------

def test_four_buys_produces_strong(monkeypatch):
    """Four BUY signals (score=4) maps to STRONG."""
    agg = SignalAggregator()
    df = make_price_df()
    hold_name = "RSI Mean-Reversion"

    def mock_generate_latest_signal(self, df_):
        if self.name == hold_name:
            return _make_mock_signal("HOLD", self.name, self.version)
        return _make_mock_signal("BUY", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert result.score == 4
    assert result.strength == AggregatedSignalStrength.STRONG
    assert hold_name in result.hold_strategies


# ---------------------------------------------------------------------------
# Test 7 — 5 BUYs → VERY_STRONG
# ---------------------------------------------------------------------------

def test_five_buys_produces_very_strong(monkeypatch):
    """All 5 BUY signals (score=5) maps to VERY_STRONG."""
    agg = SignalAggregator()
    df = make_price_df()

    def mock_generate_latest_signal(self, df_):
        return _make_mock_signal("BUY", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert result.score == 5
    assert result.strength == AggregatedSignalStrength.VERY_STRONG
    assert result.strategies_evaluated == 5
    assert result.buy_count == 5
    assert result.hold_count == 0


# ---------------------------------------------------------------------------
# Test 8 — Erroring strategy excluded from denominator
# ---------------------------------------------------------------------------

def test_erroring_strategy_excluded_from_denominator(monkeypatch):
    """A strategy that raises an exception is excluded from strategies_evaluated and score."""
    agg = SignalAggregator()
    df = make_price_df()
    error_name = "MACD Momentum"

    def mock_generate_latest_signal(self, df_):
        if self.name == error_name:
            raise RuntimeError("Simulated strategy failure")
        return _make_mock_signal("BUY", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert result.strategies_total == 5
    assert result.strategies_evaluated == 4         # one errored out
    assert result.score == 4                        # 4 BUYs out of 4 evaluated
    assert error_name in result.error_strategies
    assert result.strength == AggregatedSignalStrength.STRONG


# ---------------------------------------------------------------------------
# Test 9 — buy_strategies and hold_strategies lists are correct
# ---------------------------------------------------------------------------

def test_strategy_name_lists_are_accurate(monkeypatch):
    """buy_strategies and hold_strategies contain exactly the expected strategy names."""
    agg = SignalAggregator()
    df = make_price_df()
    buy_names = {"EMA Pullback", "Bollinger Squeeze"}
    hold_names = {"MA Trend Breakout", "MACD Momentum", "RSI Mean-Reversion"}

    def mock_generate_latest_signal(self, df_):
        if self.name in buy_names:
            return _make_mock_signal("BUY", self.name, self.version)
        return _make_mock_signal("HOLD", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert set(result.buy_strategies) == buy_names
    assert set(result.hold_strategies) == hold_names
    assert len(result.votes) == 5


# ---------------------------------------------------------------------------
# Test 10 — Determinism: same input → identical output
# ---------------------------------------------------------------------------

def test_aggregation_is_deterministic(monkeypatch):
    """Running aggregate twice on the same DataFrame produces identical results."""
    agg = SignalAggregator()
    df = make_price_df()

    call_count = {"n": 0}

    def mock_generate_latest_signal(self, df_):
        call_count["n"] += 1
        if self.name in {"EMA Pullback", "MACD Momentum"}:
            return _make_mock_signal("BUY", self.name, self.version)
        return _make_mock_signal("HOLD", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result_1 = agg.aggregate(symbol="TESTSYM", df=df)
    result_2 = agg.aggregate(symbol="TESTSYM", df=df)

    assert result_1.score == result_2.score
    assert result_1.strength == result_2.strength
    assert result_1.buy_strategies == result_2.buy_strategies
    assert result_1.hold_strategies == result_2.hold_strategies
    assert result_1.buy_count == result_2.buy_count


# ---------------------------------------------------------------------------
# Test 11 — best_* fields come from the first BUY-voting strategy
# ---------------------------------------------------------------------------

def test_best_fields_come_from_first_buy_strategy(monkeypatch):
    """best_entry_price / best_stop_loss / best_target_price come from the first BUY vote."""
    agg = SignalAggregator()
    df = make_price_df()

    # ema_pullback is first in PRODUCTION_STRATEGY_KEYS → its trade params should win
    first_buy_name = "EMA Pullback"

    def mock_generate_latest_signal(self, df_):
        from backend.strategies.models import SignalType, StrategySignal
        if self.name in {first_buy_name, "MACD Momentum"}:
            # Both return BUY but with different prices
            price = 200.0 if self.name == first_buy_name else 999.0
            return StrategySignal(
                symbol="TESTSYM",
                strategy_name=self.name,
                strategy_version=self.version,
                signal=SignalType.BUY,
                signal_date="2024-08-22",
                entry_price=price,
                stop_loss=price - 5,
                target_price=price + 10,
            )
        return _make_mock_signal("HOLD", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert result.best_strategy_name == first_buy_name
    assert result.best_entry_price == 200.0
    assert result.best_stop_loss == 195.0
    assert result.best_target_price == 210.0


# ---------------------------------------------------------------------------
# Test 12 — best_* fields are None when no strategy produces BUY
# ---------------------------------------------------------------------------

def test_best_fields_none_when_no_buy(monkeypatch):
    """When no strategy produces BUY, all best_* fields are None."""
    agg = SignalAggregator()
    df = make_price_df()

    def mock_generate_latest_signal(self, df_):
        return _make_mock_signal("HOLD", self.name, self.version)

    from backend.strategies import (
        EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
        MACDMomentumStrategy, BollingerSqueezeStrategy,
    )
    for cls in [EMAPullbackStrategy, MATrendBreakoutStrategy, RSIMeanReversionStrategy,
                MACDMomentumStrategy, BollingerSqueezeStrategy]:
        monkeypatch.setattr(cls, "generate_latest_signal", mock_generate_latest_signal)

    result = agg.aggregate(symbol="TESTSYM", df=df)

    assert result.best_entry_price is None
    assert result.best_stop_loss is None
    assert result.best_target_price is None
    assert result.best_strategy_name is None


# ---------------------------------------------------------------------------
# Test 13 — strategies_total reflects number of keys attempted
# ---------------------------------------------------------------------------

def test_strategies_total_reflects_keys_attempted(monkeypatch):
    """strategies_total equals len(strategy_keys) passed to aggregate()."""
    agg = SignalAggregator()
    df = make_price_df()

    def mock_generate_latest_signal(self, df_):
        return _make_mock_signal("BUY", self.name, self.version)

    from backend.strategies import EMAPullbackStrategy, MACDMomentumStrategy
    monkeypatch.setattr(EMAPullbackStrategy, "generate_latest_signal", mock_generate_latest_signal)
    monkeypatch.setattr(MACDMomentumStrategy, "generate_latest_signal", mock_generate_latest_signal)

    # Only run 2 strategies explicitly
    result = agg.aggregate(
        symbol="TESTSYM",
        df=df,
        strategy_keys=["ema_pullback", "macd_momentum"],
    )

    assert result.strategies_total == 2
    assert result.strategies_evaluated == 2
    assert result.score == 2
    assert result.strength == AggregatedSignalStrength.WEAK
