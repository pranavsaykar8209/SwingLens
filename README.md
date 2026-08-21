# SwingLens

## Description
SwingLens is a monorepo application structured with a React frontend, a FastAPI backend, a market-data ingestion engine for Indian equities, point-in-time index constituent tracking, a reusable technical indicator engine, and an extensible strategy engine framework.

## Technology Stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, ESLint
- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic
- **Market Data & Storage:** SQLite, yfinance, pandas, numpy, httpx
- **Testing:** Pytest

---

## Strategy Engine Framework Architecture

The **Strategy Engine Framework** provides a decoupled, strongly typed abstraction for swing trading strategies. It isolates signal generation logic from database storage, UI rendering, and backtester execution.

```
backend/
├── strategies/
│   ├── __init__.py         # Package exports
│   ├── models.py           # SignalType Enum & StrategySignal Pydantic model
│   ├── base.py             # Abstract BaseStrategy class & metadata definitions
│   ├── registry.py         # StrategyRegistry for discovery & lookup
│   └── examples/
│       ├── __init__.py
│       └── example_strategy.py # Non-trading PassthroughHoldStrategy demonstrator
```

### Signal Model (`StrategySignal`)
Signals emitted by strategies follow a strict Pydantic model:
- `symbol`: Equity symbol (e.g. `COALINDIA`)
- `strategy_name`: Name of strategy (e.g. `Passthrough Hold Strategy`)
- `strategy_version`: Version string (e.g. `1.0.0`)
- `signal`: `BUY` | `SELL` | `HOLD` | `WATCH`
- `signal_date`: Date string `YYYY-MM-DD`
- `entry_price`: Optional entry price float
- `stop_loss`: Optional stop loss float
- `target_price`: Optional target price float
- `risk_reward`: Automatically calculated `(target - entry) / (entry - stop)` ratio
- `score`: Confidence score (e.g. 0.0 - 1.0)
- `reason`: Explanation string
- `metadata`: Arbitrary strategy metadata dict

### Strict No Look-Ahead Rule
- Strategies receive historical price and indicator DataFrames sorted chronologically (`trade_date ASC`).
- Evaluated candle `i` consumes **ONLY** rows `df.iloc[:i+1]`.
- Future candles (`i+1` onwards) are strictly hidden from signal calculation logic.

### Strategy Parameters & Registry
- Strategies define configurable parameters in `default_parameters` (e.g. `{"ema_fast": 20, "ema_slow": 50}`).
- New strategies register with the central registry via `@register_strategy`:
  ```python
  from backend.strategies import BaseStrategy, register_strategy, SignalType, StrategySignal

  @register_strategy
  class MyStrategy(BaseStrategy):
      name = "My Strategy"
      version = "1.0.0"
      default_parameters = {"rsi_period": 14}

      def generate_signals(self, df):
          ...
  ```
- Strategies are instantiated by name via `get_strategy("My Strategy", parameters={...})`.
- Registry listing via `list_strategies()` returns metadata for all available strategies.

---

## Strategy Framework vs Backtesting & Scanner

| Layer | Responsibility |
| :--- | :--- |
| **Indicator Engine** | Computes in-memory technical indicators (EMA, RSI, ATR, RVOL) from raw OHLCV prices. |
| **Strategy Engine** | Consumes OHLCV + indicators and emits structured `StrategySignal` objects (`BUY`, `SELL`, `HOLD`, `WATCH`). Does not handle trade execution. |
| **Scanner Engine (Future)** | Iterates universe, runs active strategies on latest candle (`generate_latest_signal`), filters high-confidence setups for UI display. |
| **Backtesting Engine (Future)** | Feeds historical data candle-by-candle into strategies, simulates orders, tracks slippage/fees, and calculates portfolio metrics (Sharpe, drawdown, win rate). |

---

## Commands for Local Setup & Testing

### 1. Run Unit Tests
```bash
PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests
```

### 2. Register & Inspect Available Strategies
```python
from backend.strategies import list_strategies, get_strategy

# List metadata for all registered strategies
all_strategies = list_strategies()

# Instantiate strategy with custom parameters
strategy = get_strategy("Passthrough Hold Strategy", parameters={"holding_note": "Custom note"})
```
