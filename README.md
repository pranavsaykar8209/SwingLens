# SwingLens

## Description
SwingLens is a monorepo application structured with a React frontend, a FastAPI backend, a market-data ingestion engine for Indian equities, point-in-time index constituent tracking, a reusable technical indicator engine, an extensible strategy engine framework, an event-driven backtesting engine, and real research strategies.

## Technology Stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, ESLint
- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic
- **Market Data & Storage:** SQLite, yfinance, pandas, numpy, httpx
- **Testing:** Pytest

---

## Strategy: EMA Pullback v1.0

The **EMA Pullback v1.0** strategy is a research strategy designed to identify high-probability long swing entries in strong bullish trends when price pulls back near the EMA20 and confirms momentum and volume expansion.

```
backend/
├── strategies/
│   ├── ema_pullback.py         # EMA Pullback v1.0 strategy implementation
│   ├── base.py                 # Abstract BaseStrategy interface
│   ├── registry.py             # StrategyRegistry
│   └── models.py               # SignalType & StrategySignal
└── scripts/
    └── backtest_strategy.py    # CLI runner to backtest strategies against SQLite DB
```

---

## Strategy Rules & Specifications

### 1. Default Parameters
- `ema_fast`: `20`
- `ema_trend`: `50`
- `ema_long`: `200`
- `rsi_period`: `14`
- `rsi_min`: `50.0`
- `rsi_max`: `65.0`
- `atr_period`: `14`
- `atr_stop_multiplier`: `1.5`
- `reward_risk_ratio`: `2.0`
- `pullback_distance_percent`: `2.0`
- `volume_period`: `20`
- `volume_multiplier`: `1.0`

### 2. Long Entry Setup (ALL 8 conditions required on Candle N)
1. **Fast Trend:** `EMA20 > EMA50`
2. **Long-term Trend:** `EMA50 > EMA200`
3. **Price Level:** `Close > EMA200`
4. **Pullback to EMA20:** `abs(Close - EMA20) / EMA20 <= 0.02` (within 2% of EMA20)
5. **RSI Momentum:** `50.0 <= RSI14 <= 65.0`
6. **Bullish Confirmation:** `Close_N > High_{N-1}` (Current candle close breaks previous candle high)
7. **Volume Confirmation:** `Volume_N >= Volume_SMA20 * 1.0`
8. **Data Availability:** `ATR14` and all required indicators are not `NaN`.

### 3. Stop-Loss & Target Calculations
- **Entry Price:** Candle $N$ Close (Backtest Engine executes at Candle $N+1$ Open)
- **Stop Loss:** $\text{Stop Loss} = \text{Entry Price} - (\text{ATR14} \times 1.5)$
- **Target Price:** $\text{Target Price} = \text{Entry Price} + (\text{Entry Price} - \text{Stop Loss}) \times 2.0$ (2R Reward-to-Risk)

### 4. No Look-Ahead & Parameter Discipline
- Signal evaluation uses ONLY historical data up to the current candle $N$.
- **No Parameter Optimization:** Parameters are fixed at default research values. No curve-fitting or tuning was performed on historical datasets.

---

## Running Strategy Backtests

### 1. Single Stock Backtest (e.g. ABB)
```bash
PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.backtest_strategy --strategy ema_pullback --symbol ABB
```

### 2. Full Nifty Next 50 Universe Backtest
```bash
PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.backtest_strategy --strategy ema_pullback --universe nifty_next_50
```

### 3. Run All Unit Tests
```bash
PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests
```
