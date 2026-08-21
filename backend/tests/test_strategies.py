import pandas as pd
import pytest

from backend.strategies import (
    BaseStrategy,
    SignalType,
    StrategyRegistry,
    StrategySignal,
    get_strategy,
    list_strategies,
    register_strategy,
    PassthroughHoldStrategy,
)
from backend.strategies.models import calculate_risk_reward_ratio


# Custom dummy strategy for testing custom parameter overrides & signals
class DummyTestStrategy(BaseStrategy):
    name: str = "Dummy Test Strategy"
    version: str = "1.0.0"
    description: str = "Test strategy"
    default_parameters: dict = {"ema_fast": 20, "ema_slow": 50}

    def generate_signals(self, df: pd.DataFrame) -> list[StrategySignal]:
        signals = []
        for idx, row in df.iterrows():
            signals.append(
                StrategySignal(
                    symbol="COALINDIA",
                    strategy_name=self.name,
                    strategy_version=self.version,
                    signal=SignalType.BUY,
                    signal_date=row["trade_date"],
                    entry_price=100.0,
                    stop_loss=90.0,
                    target_price=120.0,
                    reason="Test buy signal",
                )
            )
        return signals


# 1. Base Strategy Interface Test
def test_base_strategy_interface():
    strat = PassthroughHoldStrategy()
    meta = strat.get_metadata()
    assert meta["name"] == "Passthrough Hold Strategy"
    assert meta["version"] == "1.0.0"
    assert "supported_signal_types" in meta


# 2. Signal Model Validation Test
def test_signal_model_validation():
    sig = StrategySignal(
        symbol="COALINDIA",
        strategy_name="TestStrat",
        strategy_version="1.0.0",
        signal=SignalType.BUY,
        signal_date="2024-01-01",
    )
    assert sig.symbol == "COALINDIA"
    assert sig.signal == SignalType.BUY
    assert sig.signal_date == "2024-01-01"


# 3. BUY Signal Creation & Risk/Reward Test
def test_buy_signal_creation():
    sig = StrategySignal(
        symbol="COALINDIA",
        strategy_name="BuyStrat",
        strategy_version="1.0.0",
        signal=SignalType.BUY,
        signal_date="2024-01-01",
        entry_price=100.0,
        stop_loss=90.0,
        target_price=120.0,
    )
    # Risk = 10 (100 - 90), Reward = 20 (120 - 100), R:R = 2.0
    assert sig.signal == SignalType.BUY
    assert sig.risk_reward == 2.0


# 4. SELL Signal Creation Test
def test_sell_signal_creation():
    sig = StrategySignal(
        symbol="COALINDIA",
        strategy_name="SellStrat",
        strategy_version="1.0.0",
        signal=SignalType.SELL,
        signal_date="2024-01-01",
        entry_price=100.0,
        stop_loss=110.0,
        target_price=80.0,
    )
    # Risk = 10 (110 - 100), Reward = 20 (100 - 80), R:R = 2.0
    assert sig.signal == SignalType.SELL
    assert sig.risk_reward == 2.0


# 5. HOLD Signal Creation Test
def test_hold_signal_creation():
    sig = StrategySignal(
        symbol="COALINDIA",
        strategy_name="HoldStrat",
        strategy_version="1.0.0",
        signal=SignalType.HOLD,
        signal_date="2024-01-01",
    )
    assert sig.signal == SignalType.HOLD


# 6. WATCH Signal Creation Test
def test_watch_signal_creation():
    sig = StrategySignal(
        symbol="COALINDIA",
        strategy_name="WatchStrat",
        strategy_version="1.0.0",
        signal=SignalType.WATCH,
        signal_date="2024-01-01",
        reason="Approaching support zone",
    )
    assert sig.signal == SignalType.WATCH
    assert sig.reason == "Approaching support zone"


# 7. Strategy Parameters Test (Defaults & Custom Overrides)
def test_strategy_parameters():
    strat_default = DummyTestStrategy()
    assert strat_default.parameters == {"ema_fast": 20, "ema_slow": 50}

    strat_custom = DummyTestStrategy(parameters={"ema_fast": 10, "rsi_period": 14})
    assert strat_custom.parameters == {"ema_fast": 10, "ema_slow": 50, "rsi_period": 14}


# 8. Strategy Registry Core Test
def test_strategy_registry():
    reg = StrategyRegistry()
    reg.register(DummyTestStrategy)
    assert "dummy_test_strategy" in reg.list_names()


# 9. Registering a Strategy Class Test
def test_register_strategy():
    register_strategy(DummyTestStrategy)
    strategies = list_strategies()
    names = [s["name"] for s in strategies]
    assert "Dummy Test Strategy" in names


# 10. Finding a Strategy by Name Test
def test_get_strategy_by_name():
    register_strategy(DummyTestStrategy)
    inst = get_strategy("Dummy Test Strategy", parameters={"ema_fast": 15})
    assert inst.name == "Dummy Test Strategy"
    assert inst.parameters["ema_fast"] == 15


# 11. Listing Strategies Test
def test_list_strategies():
    strats = list_strategies()
    assert isinstance(strats, list)
    assert len(strats) >= 1
    for s in strats:
        assert "name" in s
        assert "version" in s


# 12. Unknown Strategy Handling Test
def test_unknown_strategy_handling():
    with pytest.raises(KeyError) as exc_info:
        get_strategy("NonExistentStrategy123")
    assert "Unknown strategy" in str(exc_info.value)


# 13. Example Strategy Test
def test_example_strategy():
    df = pd.DataFrame({
        "symbol": ["COALINDIA", "COALINDIA"],
        "trade_date": ["2024-01-01", "2024-01-02"],
        "close": [100.0, 102.0],
    })
    strat = PassthroughHoldStrategy()
    signals = strat.generate_signals(df)

    assert len(signals) == 2
    assert signals[0].signal == SignalType.HOLD
    assert signals[1].signal == SignalType.HOLD

    latest_sig = strat.generate_latest_signal(df)
    assert latest_sig is not None
    assert latest_sig.signal_date == "2024-01-02"


# 14. Ensure Strategy Does Not Require Future Candles (No-Lookahead Test)
def test_no_lookahead_guarantee():
    class SequentialCheckStrategy(BaseStrategy):
        name = "Sequential Check Strategy"

        def generate_signals(self, df: pd.DataFrame) -> list[StrategySignal]:
            signals = []
            # On candle i, evaluate only df.iloc[:i+1]
            for i in range(len(df)):
                sub_df = df.iloc[: i + 1]
                latest_close = sub_df["close"].iloc[-1]
                signals.append(
                    StrategySignal(
                        symbol="TEST",
                        strategy_name=self.name,
                        strategy_version=self.version,
                        signal=SignalType.BUY if latest_close > 100 else SignalType.HOLD,
                        signal_date=sub_df["trade_date"].iloc[-1],
                    )
                )
            return signals

    df_base = pd.DataFrame({
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "close": [95.0, 105.0, 110.0],
    })

    df_modified_future = pd.DataFrame({
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "close": [95.0, 105.0, 999.0],  # Future candle 2 changed
    })

    strat = SequentialCheckStrategy()
    sig_base = strat.generate_signals(df_base)
    sig_mod = strat.generate_signals(df_modified_future)

    # Candle 0 and Candle 1 signals MUST be identical regardless of Candle 2 changes
    assert sig_base[0].signal == sig_mod[0].signal == SignalType.HOLD
    assert sig_base[1].signal == sig_mod[1].signal == SignalType.BUY
