import pandas as pd
import pytest
from backend.research.validator import (
    DEFAULT_REPRESENTATIVE_SAMPLE,
    ValidationConfig,
    StrategyValidator,
)
from backend.strategies.registry import list_strategies


def create_synthetic_data(symbol: str, count: int = 150) -> pd.DataFrame:
    dates = pd.date_range(start="2025-01-01", periods=count, freq="D")
    prices = [100.0 + i * 0.5 for i in range(count)]
    return pd.DataFrame(
        {
            "trade_date": dates.strftime("%Y-%m-%d"),
            "symbol": symbol,
            "open": prices,
            "high": [p + 1.0 for p in prices],
            "low": [p - 1.0 for p in prices],
            "close": prices,
            "volume": [1000] * count,
        }
    )


def test_1_strategy_discovery(monkeypatch):
    monkeypatch.setattr(
        "backend.research.validator.get_price_history",
        lambda conn, symbol, start_date=None, end_date=None: create_synthetic_data(symbol),
    )
    monkeypatch.setattr(
        "backend.research.validator.get_active_universe_constituents",
        lambda conn, index_name: [{"symbol": "BANKBARODA"}],
    )

    config = ValidationConfig(symbols=["BANKBARODA"])
    validator = StrategyValidator(config)
    report = validator.run()

    eval_names = set(m.strategy_name for m in report.strategy_metrics)
    assert len(report.strategy_metrics) >= 5
    assert "EMA Pullback" in eval_names
    assert "MA Trend Breakout" in eval_names
    assert "RSI Mean-Reversion" in eval_names
    assert "MACD Momentum" in eval_names
    assert "Bollinger Squeeze" in eval_names


def test_2_selected_stock_filtering(monkeypatch):
    monkeypatch.setattr(
        "backend.research.validator.get_price_history",
        lambda conn, symbol, start_date=None, end_date=None: create_synthetic_data(symbol),
    )
    monkeypatch.setattr(
        "backend.research.validator.get_active_universe_constituents",
        lambda conn, index_name: [{"symbol": "BANKBARODA"}, {"symbol": "CHOLAFIN"}],
    )

    config = ValidationConfig(symbols=["BANKBARODA", "CHOLAFIN"])
    validator = StrategyValidator(config)
    report = validator.run()

    for m in report.strategy_metrics:
        assert m.stocks_tested == 2
        assert set(m.per_stock_results.keys()) == {"BANKBARODA", "CHOLAFIN"}


def test_3_unknown_symbol_handling(monkeypatch):
    monkeypatch.setattr(
        "backend.research.validator.get_price_history",
        lambda conn, symbol, start_date=None, end_date=None: create_synthetic_data(symbol) if symbol == "BANKBARODA" else pd.DataFrame(),
    )
    monkeypatch.setattr(
        "backend.research.validator.get_active_universe_constituents",
        lambda conn, index_name: [{"symbol": "BANKBARODA"}],
    )

    config = ValidationConfig(symbols=["INVALID_SYM_XYZ", "BANKBARODA"])
    validator = StrategyValidator(config)
    report = validator.run()

    for m in report.strategy_metrics:
        assert "INVALID_SYM_XYZ" not in m.per_stock_results
        assert "BANKBARODA" in m.per_stock_results
        assert m.stocks_tested == 1


def test_4_missing_historical_data_handling(monkeypatch):
    def mock_get_history(conn, symbol, start_date=None, end_date=None):
        if symbol == "TMCV":
            return create_synthetic_data(symbol, count=50)  # Insufficient candles < min_candles=100
        return create_synthetic_data(symbol, count=150)

    monkeypatch.setattr("backend.research.validator.get_price_history", mock_get_history)
    monkeypatch.setattr(
        "backend.research.validator.get_active_universe_constituents",
        lambda conn, index_name: [{"symbol": "BANKBARODA"}, {"symbol": "TMCV"}],
    )

    config = ValidationConfig(symbols=["TMCV", "BANKBARODA"], min_candles=100)
    validator = StrategyValidator(config)
    report = validator.run()

    for m in report.strategy_metrics:
        assert "TMCV" not in m.per_stock_results
        assert "BANKBARODA" in m.per_stock_results


def test_5_all_strategies_executed(monkeypatch):
    monkeypatch.setattr(
        "backend.research.validator.get_price_history",
        lambda conn, symbol, start_date=None, end_date=None: create_synthetic_data(symbol),
    )
    monkeypatch.setattr(
        "backend.research.validator.get_active_universe_constituents",
        lambda conn, index_name: [{"symbol": "BANKBARODA"}],
    )

    config = ValidationConfig(symbols=["BANKBARODA"])
    validator = StrategyValidator(config)
    report = validator.run()

    assert len(report.strategy_metrics) >= 5
    for m in report.strategy_metrics:
        assert "BANKBARODA" in m.per_stock_results


def test_6_and_7_aggregation_and_metrics(monkeypatch):
    monkeypatch.setattr(
        "backend.research.validator.get_price_history",
        lambda conn, symbol, start_date=None, end_date=None: create_synthetic_data(symbol),
    )
    monkeypatch.setattr(
        "backend.research.validator.get_active_universe_constituents",
        lambda conn, index_name: [{"symbol": "BANKBARODA"}, {"symbol": "DIVISLAB"}],
    )

    config = ValidationConfig(symbols=["BANKBARODA", "DIVISLAB"])
    validator = StrategyValidator(config)
    report = validator.run()

    for m in report.strategy_metrics:
        sum_trades = sum(r.total_trades for r in m.per_stock_results.values())
        sum_wins = sum(r.winning_trades for r in m.per_stock_results.values())
        sum_losses = sum(r.losing_trades for r in m.per_stock_results.values())

        assert m.total_trades == sum_trades
        assert m.winning_trades == sum_wins
        assert m.losing_trades == sum_losses
        if sum_trades > 0:
            assert round(m.win_rate_pct, 1) == round(sum_wins / sum_trades * 100.0, 1)


def test_8_no_universe_expansion(monkeypatch):
    monkeypatch.setattr(
        "backend.research.validator.get_price_history",
        lambda conn, symbol, start_date=None, end_date=None: create_synthetic_data(symbol),
    )
    monkeypatch.setattr(
        "backend.research.validator.get_active_universe_constituents",
        lambda conn, index_name: [{"symbol": "BANKBARODA"}, {"symbol": "CHOLAFIN"}, {"symbol": "DIVISLAB"}],
    )

    config = ValidationConfig(symbols=["BANKBARODA", "CHOLAFIN", "DIVISLAB"])
    validator = StrategyValidator(config)
    report = validator.run()

    for m in report.strategy_metrics:
        assert m.stocks_tested == 3
        assert len(m.per_stock_results) == 3


def test_9_deterministic_results(monkeypatch):
    monkeypatch.setattr(
        "backend.research.validator.get_price_history",
        lambda conn, symbol, start_date=None, end_date=None: create_synthetic_data(symbol),
    )
    monkeypatch.setattr(
        "backend.research.validator.get_active_universe_constituents",
        lambda conn, index_name: [{"symbol": "BANKBARODA"}, {"symbol": "TVSMOTOR"}],
    )

    config = ValidationConfig(symbols=["BANKBARODA", "TVSMOTOR"])
    validator1 = StrategyValidator(config)
    report1 = validator1.run()

    validator2 = StrategyValidator(config)
    report2 = validator2.run()

    for m1, m2 in zip(report1.strategy_metrics, report2.strategy_metrics):
        assert m1.strategy_name == m2.strategy_name
        assert m1.total_trades == m2.total_trades
        assert m1.winning_trades == m2.winning_trades
        assert m1.win_rate_pct == m2.win_rate_pct
        assert m1.total_r == m2.total_r
        assert m1.average_r == m2.average_r
