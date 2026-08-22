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

---

## Daily Market Scanner

The **Daily Market Scanner** (`backend/scanner/`) is a backend service designed to identify stocks matching strategy setup conditions on the latest completed daily candle.

### Key Characteristics:
- **Purpose:** Answers *"Which current Nifty Next 50 stocks satisfy EMA Pullback v1.0 on the latest completed daily candle?"*
- **Dynamic Universe:** Loads active constituents of `NIFTY_NEXT_50` directly from SQLite `index_memberships` (point-in-time membership tracking).
- **Strategy Used:** `EMA Pullback v1.0` via the standard `BaseStrategy` interface.
- **Offline Operation:** Operates 100% offline using existing local daily price history stored in `data/swinglens.db`. Does not download market data or modify database tables.
- **Strict No-Lookahead Rule:** Evaluates signals using only completed daily candles available at or before the scan date.
- **Error Isolation:** If price data for an individual stock is incomplete (< 200 candles), the scanner returns an `ERROR` `ScanResult` for that stock without halting the overall scan loop.
- **Structured Data Models:** Returns `ScanResult` and `ScanSummary` Pydantic models designed for direct JSON serialization through FastAPI endpoints and UI consumption by the React frontend.
- **Development CLI:** A developer CLI tool is available for terminal testing:
  ```bash
  PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.run_scanner
  ```

---

## FastAPI Backend Endpoints

### 1. Health Check
`GET /health`
- **Response:** `{"status": "ok"}`

### 2. Latest Scanner Results
`GET /api/scanner/latest`
- **Description:** Returns daily market scan results across the active index universe for the requested strategy.
- **Query Parameters:**
  - `strategy` (optional, default: `ema_pullback`): Strategy identifier string registered in `StrategyRegistry`. Returns `HTTP 400` if unknown.
  - `index` (optional, default: `NIFTY_NEXT_50`): Target index universe name in `index_memberships`.
- **CORS Configuration:** Configured for local development origins (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`).

#### Example JSON Response:
```json
{
  "scan_date": "2026-08-20",
  "universe": "NIFTY_NEXT_50",
  "strategy": "EMA Pullback",
  "strategy_version": "1.0",
  "stocks_scanned": 50,
  "buy_count": 2,
  "watch_count": 0,
  "hold_count": 47,
  "skip_count": 1,
  "results": [
    {
      "symbol": "HINDZINC",
      "company_name": "Hindustan Zinc Ltd.",
      "signal": "BUY",
      "signal_date": "2026-08-20",
      "close": 573.9,
      "entry_price": 573.9,
      "stop_loss": 550.27,
      "target_price": 621.16,
      "risk_reward": 2.0,
      "score": 0.85,
      "strategy_name": "EMA Pullback",
      "strategy_version": "1.0",
      "reason": "EMA20 (568.10) > EMA50 (550.20) > EMA200 (510.40)...",
      "metadata": {
        "rsi14": 58.4
      },
      "error": null,
      "status": "SUCCESS"
    }
  ]
}
```

### 3. Single-Stock Backtest
`GET /api/backtest/{symbol}`
- **Description:** Executes an on-demand single-stock strategy backtest querying daily price history strictly for `{symbol}`.
- **Query Parameters:**
  - `strategy` (optional, default: `ema_pullback`): Strategy identifier string.
  - `start_date` (optional, YYYY-MM-DD): Start date threshold.
  - `end_date` (optional, YYYY-MM-DD): End date threshold.

---

## How to Run the Application

Run both the FastAPI backend and Vite React frontend with a single command from the project root:

```bash
npm run dev
```

- **Backend API:** `http://localhost:8000` (API Docs: `http://localhost:8000/docs`)
- **Frontend Dashboard:** `http://localhost:5173`

