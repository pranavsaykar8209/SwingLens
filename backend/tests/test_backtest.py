import pandas as pd
import pytest

from backend.backtest import (
    BacktestConfig,
    BacktestEngine,
    ExitReason,
    Portfolio,
    Trade,
    calculate_execution_price,
    calculate_transaction_costs,
    calculate_performance_metrics,
)
from backend.strategies.base import BaseStrategy
from backend.strategies.models import SignalType, StrategySignal


# Dummy strategy for backtest testing
class CustomSignalStrategy(BaseStrategy):
    name = "Custom Signal Strategy"
    version = "1.0.0"

    def __init__(self, signals_map=None):
        super().__init__()
        # signals_map: {index: (SignalType, stop_loss, target_price)}
        self.signals_map = signals_map or {}

    def generate_signals(self, df: pd.DataFrame) -> list[StrategySignal]:
        signals = []
        if df.empty:
            return signals

        idx = len(df) - 1
        sym = df["symbol"].iloc[0] if "symbol" in df.columns else "TEST"
        trade_date = df["trade_date"].iloc[-1]

        if idx in self.signals_map:
            sig_type, sl, tp = self.signals_map[idx]
            signals.append(
                StrategySignal(
                    symbol=sym,
                    strategy_name=self.name,
                    strategy_version=self.version,
                    signal=sig_type,
                    signal_date=trade_date,
                    stop_loss=sl,
                    target_price=tp,
                )
            )

        return signals


# 1. Buy and Profitable Target Exit Test
def test_buy_and_target_exit():
    df = pd.DataFrame({
        "symbol": ["TEST"] * 5,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        "open": [100.0, 100.0, 105.0, 115.0, 115.0],
        "high": [102.0, 102.0, 110.0, 122.0, 120.0],
        "low": [98.0, 98.0, 104.0, 114.0, 114.0],
        "close": [100.0, 100.0, 108.0, 120.0, 118.0],
        "volume": [1000] * 5,
    })

    # Signal BUY at candle 0 close (idx 0), SL 90, TP 120
    strat = CustomSignalStrategy({0: (SignalType.BUY, 90.0, 120.0)})
    config = BacktestConfig(commission_pct=0.0, slippage_pct=0.0)
    engine = BacktestEngine(strat, config)

    res = engine.run(df)
    assert len(res.trades) == 1
    t = res.trades[0]
    assert t.entry_date == "2024-01-02"  # Executed at candle 1 OPEN
    assert t.exit_reason == ExitReason.TARGET.value
    assert t.net_pnl > 0


# 2. Buy and Stop Loss Exit Test
def test_buy_and_stop_loss_exit():
    df = pd.DataFrame({
        "symbol": ["TEST"] * 5,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        "open": [100.0, 100.0, 95.0, 85.0, 85.0],
        "high": [102.0, 102.0, 96.0, 86.0, 86.0],
        "low": [98.0, 98.0, 88.0, 80.0, 80.0],
        "close": [100.0, 100.0, 90.0, 82.0, 82.0],
        "volume": [1000] * 5,
    })

    # Signal BUY at candle 0 close, SL 90, TP 120
    strat = CustomSignalStrategy({0: (SignalType.BUY, 90.0, 120.0)})
    config = BacktestConfig(commission_pct=0.0, slippage_pct=0.0)
    engine = BacktestEngine(strat, config)

    res = engine.run(df)
    assert len(res.trades) == 1
    t = res.trades[0]
    assert t.exit_reason == ExitReason.STOP_LOSS.value
    assert t.net_pnl < 0


# 3. Signal Exit Test (SELL signal)
def test_signal_exit():
    df = pd.DataFrame({
        "symbol": ["TEST"] * 5,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        "open": [100.0, 100.0, 105.0, 105.0, 105.0],
        "high": [102.0, 102.0, 107.0, 107.0, 107.0],
        "low": [98.0, 98.0, 103.0, 103.0, 103.0],
        "close": [100.0, 100.0, 106.0, 106.0, 106.0],
        "volume": [1000] * 5,
    })

    # BUY at candle 0 (idx 0), SELL at candle 2 (idx 2)
    strat = CustomSignalStrategy({
        0: (SignalType.BUY, None, None),
        2: (SignalType.SELL, None, None),
    })
    config = BacktestConfig(commission_pct=0.0, slippage_pct=0.0)
    engine = BacktestEngine(strat, config)

    res = engine.run(df)
    assert len(res.trades) == 1
    t = res.trades[0]
    assert t.exit_reason == ExitReason.SIGNAL.value
    assert t.exit_date == "2024-01-04"  # Executed at candle 3 OPEN


# 4. End-of-Backtest Exit Test
def test_end_of_backtest_exit():
    df = pd.DataFrame({
        "symbol": ["TEST"] * 3,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [100.0, 100.0, 102.0],
        "high": [102.0, 102.0, 103.0],
        "low": [98.0, 98.0, 101.0],
        "close": [100.0, 100.0, 102.0],
        "volume": [1000] * 3,
    })

    # BUY at candle 0, no SL/TP/SELL signal -> closed at end of backtest
    strat = CustomSignalStrategy({0: (SignalType.BUY, None, None)})
    config = BacktestConfig(commission_pct=0.0, slippage_pct=0.0)
    engine = BacktestEngine(strat, config)

    res = engine.run(df)
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == ExitReason.END_OF_BACKTEST.value


# 5. Next-Candle Execution Test
def test_next_candle_execution():
    df = pd.DataFrame({
        "symbol": ["TEST"] * 3,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [100.0, 108.0, 108.0],
        "high": [102.0, 110.0, 110.0],
        "low": [98.0, 107.0, 107.0],
        "close": [100.0, 109.0, 109.0],
        "volume": [1000] * 3,
    })

    strat = CustomSignalStrategy({0: (SignalType.BUY, None, None)})
    config = BacktestConfig(commission_pct=0.0, slippage_pct=0.0)
    engine = BacktestEngine(strat, config)

    res = engine.run(df)
    assert len(res.trades) == 1
    # Entry MUST be candle 1 OPEN (108.0), NOT candle 0 CLOSE (100.0)
    assert res.trades[0].entry_price == 108.0
    assert res.trades[0].entry_date == "2024-01-02"


# 6. Commission & Slippage Calculations
def test_commission_and_slippage():
    p_buy = calculate_execution_price(100.0, is_buy=True, slippage_pct=0.01)
    assert p_buy == 101.0  # +1% slippage on buy

    p_sell = calculate_execution_price(100.0, is_buy=False, slippage_pct=0.01)
    assert p_sell == 99.0  # -1% slippage on sell

    costs = calculate_transaction_costs(10000.0, commission_pct=0.001)
    assert costs == 10.0  # 0.1% of 10,000


# 7. Position Sizing (Fixed & Risk-based)
def test_position_sizing():
    config = BacktestConfig(initial_capital=100000.0, position_size_type="fixed", position_size_value=0.10, max_positions=5)
    port = Portfolio(config)

    # Fixed 10% of 100k = 10,000 / entry 100 = 100 qty
    qty_fixed = port.calculate_quantity(entry_price=100.0, stop_loss=90.0, current_equity=100000.0)
    assert qty_fixed == 100

    config_risk = BacktestConfig(initial_capital=100000.0, position_size_type="risk", position_size_value=0.01, max_positions=5)
    port_risk = Portfolio(config_risk)

    # 1% risk of 100k = 1,000 risk / per share risk 10 (100 - 90) = 100 qty
    qty_risk = port_risk.calculate_quantity(entry_price=100.0, stop_loss=90.0, current_equity=100000.0)
    assert qty_risk == 100


# 8. Insufficient Capital Rejection Test
def test_insufficient_capital():
    config = BacktestConfig(initial_capital=50.0)  # Very low cash
    port = Portfolio(config)
    qty = port.calculate_quantity(entry_price=100.0, stop_loss=90.0, current_equity=50.0)
    assert qty == 0


# 9. Max Positions Limit Test
def test_max_positions_limit():
    config = BacktestConfig(max_positions=1)
    port = Portfolio(config)
    port.open_position("STOCKA", "Strat", "1.0", "2024-01-01", 100.0, 10)
    assert port.can_open_position("STOCKB") is False


# 10. Ambiguous Stop/Target Candle & Conservative Policy Test
def test_ambiguous_stop_target_candle():
    df = pd.DataFrame({
        "symbol": ["TEST"] * 3,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [100.0, 100.0, 100.0],
        "high": [102.0, 102.0, 130.0],  # Candle 2 touches TP (120) and SL (80)
        "low": [98.0, 98.0, 75.0],
        "close": [100.0, 100.0, 105.0],
        "volume": [1000] * 3,
    })

    # BUY at candle 0, SL=80, TP=120
    strat = CustomSignalStrategy({0: (SignalType.BUY, 80.0, 120.0)})
    config = BacktestConfig(commission_pct=0.0, slippage_pct=0.0, ambiguity_policy="conservative")
    engine = BacktestEngine(strat, config)

    res = engine.run(df)
    assert len(res.trades) == 1
    # Conservative policy assumes STOP_LOSS hit first
    assert res.trades[0].exit_reason == ExitReason.STOP_LOSS.value
    assert any("Ambiguity Warning" in w for w in res.warnings)


# 11. No-Lookahead Behavior Test
def test_no_lookahead_behavior():
    class LookaheadTestStrategy(BaseStrategy):
        name = "Lookahead Test Strategy"

        def generate_signals(self, df: pd.DataFrame) -> list[StrategySignal]:
            # Evaluates only current slice
            idx = len(df) - 1
            if idx == 0:
                return [StrategySignal(symbol="TEST", strategy_name=self.name, strategy_version="1.0", signal=SignalType.BUY, signal_date=df["trade_date"].iloc[-1])]
            return []

    df1 = pd.DataFrame({
        "symbol": ["TEST"] * 3,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [100.0, 100.0, 100.0],
        "high": [102.0, 102.0, 102.0],
        "low": [98.0, 98.0, 98.0],
        "close": [100.0, 100.0, 100.0],
        "volume": [1000] * 3,
    })

    df2 = df1.copy()
    df2.iloc[2, df2.columns.get_loc("close")] = 999.0  # Future candle 2 altered

    engine1 = BacktestEngine(LookaheadTestStrategy())
    engine2 = BacktestEngine(LookaheadTestStrategy())

    res1 = engine1.run(df1)
    res2 = engine2.run(df2)

    # Trade entry at candle 1 must be identical
    assert res1.trades[0].entry_price == res2.trades[0].entry_price
    assert res1.trades[0].entry_date == res2.trades[0].entry_date


# 12. Performance Metrics (Win rate, Profit factor, Drawdown, Expectancy, Equity curve)
def test_performance_metrics():
    trades = [
        Trade(
            trade_id="1", symbol="A", strategy_name="S", strategy_version="1.0",
            entry_date="2024-01-01", entry_price=100.0, exit_date="2024-01-02", exit_price=110.0,
            quantity=10, gross_pnl=100.0, transaction_cost=0.0, slippage_cost=0.0, net_pnl=100.0,
            return_percent=10.0, holding_period=1, exit_reason="TARGET"
        ),
        Trade(
            trade_id="2", symbol="A", strategy_name="S", strategy_version="1.0",
            entry_date="2024-01-03", entry_price=100.0, exit_date="2024-01-04", exit_price=95.0,
            quantity=10, gross_pnl=-50.0, transaction_cost=0.0, slippage_cost=0.0, net_pnl=-50.0,
            return_percent=-5.0, holding_period=1, exit_reason="STOP_LOSS"
        ),
    ]

    equity_curve = [
        {"date": "2024-01-01", "cash": 100000.0, "equity": 100000.0, "drawdown": 0.0, "drawdown_percent": 0.0},
        {"date": "2024-01-02", "cash": 100100.0, "equity": 100100.0, "drawdown": 0.0, "drawdown_percent": 0.0},
        {"date": "2024-01-03", "cash": 100050.0, "equity": 100050.0, "drawdown": 50.0, "drawdown_percent": 0.05},
    ]

    metrics = calculate_performance_metrics(100000.0, 100050.0, trades, equity_curve, "2024-01-01", "2024-01-03")

    assert metrics["total_trades"] == 2
    assert metrics["win_rate_pct"] == 50.0
    assert metrics["profit_factor"] == 2.0  # 100 / 50
    assert metrics["net_profit"] == 50.0
    assert metrics["expectancy"] == 25.0  # (0.5 * 100) - (0.5 * 50)


# 13. Multi-Stock Backtest Execution Test
def test_multi_stock_backtest():
    df_a = pd.DataFrame({
        "symbol": ["STOCKA"] * 3,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [100.0, 100.0, 105.0],
        "high": [102.0, 102.0, 110.0],
        "low": [98.0, 98.0, 104.0],
        "close": [100.0, 100.0, 108.0],
        "volume": [1000] * 3,
    })

    df_b = pd.DataFrame({
        "symbol": ["STOCKB"] * 3,
        "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [200.0, 200.0, 210.0],
        "high": [202.0, 202.0, 215.0],
        "low": [198.0, 198.0, 208.0],
        "close": [200.0, 200.0, 212.0],
        "volume": [1000] * 3,
    })

    strat = CustomSignalStrategy({0: (SignalType.BUY, None, None)})
    config = BacktestConfig(max_positions=2, commission_pct=0.0, slippage_pct=0.0)
    engine = BacktestEngine(strat, config)

    res = engine.run({"STOCKA": df_a, "STOCKB": df_b})
    assert res.total_trades == 2
    symbols_traded = {t.symbol for t in res.trades}
    assert symbols_traded == {"STOCKA", "STOCKB"}
