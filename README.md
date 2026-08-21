# SwingLens

## Description
SwingLens is a monorepo application structured with a React frontend, a FastAPI backend, a market-data ingestion engine for Indian equities, point-in-time index constituent tracking, a reusable technical indicator engine, an extensible strategy engine framework, and an event-driven backtesting engine.

## Technology Stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, ESLint
- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic
- **Market Data & Storage:** SQLite, yfinance, pandas, numpy, httpx
- **Testing:** Pytest

---

## Backtesting Engine Architecture

The **Backtesting Engine** in `backend/backtest/` executes strategies candle-by-candle over historical price DataFrames with execution modeling, transaction costs, slippage, and performance analytics.

```
backend/
├── backtest/
│   ├── __init__.py         # Package exports
│   ├── models.py           # BacktestConfig, Trade, and BacktestResult models
│   ├── costs.py            # Slippage and transaction cost calculators
│   ├── portfolio.py        # Portfolio simulator & position sizing
│   ├── metrics.py          # Performance metrics (Sharpe, Sortino, Drawdown, Expectancy)
│   └── engine.py           # Event-driven BacktestEngine runner
```

---

## Key Assumptions & Rules

### 1. Execution Model (Next-Candle Open)
> [!IMPORTANT]
> Signal generated at the **CLOSE** of Candle N $\rightarrow$ Executed at the **OPEN** of Candle N+1 (plus slippage and commissions).

### 2. Transaction Costs & Slippage
- **Slippage:** Applied to execution price (`Buy = Price * (1 + Slippage)`, `Sell = Price * (1 - Slippage)`). Default `0.05%`.
- **Commissions & Fees:** Applied to trade turnover (`Trade Value * Commission %`). Default `0.1%` per leg.

### 3. Stop-Loss & Target Handling (Daily Candle Ambiguity Policy)
If a daily candle's High and Low touch **both** the Stop-Loss and Target price on the same day, daily OHLC cannot determine which level was hit first.

The engine applies a configurable ambiguity policy:
- `"conservative"` *(Default)*: Assumes `STOP_LOSS` was hit first and logs an ambiguity warning.
- `"optimistic"`: Assumes `TARGET` was hit first.
- `"skip"`: Closes at `STOP_LOSS` and logs an ambiguity warning.

### 4. Strict No Look-Ahead Guarantee
- The backtester iterates chronologically over trade dates.
- At candle N, the strategy generates signals consuming ONLY data available through candle N (`df.iloc[:N+1]`).
- Future candles (`N+1` onwards) are strictly hidden from signal generation logic.

### 5. Win Rate vs Profitability
> [!NOTE]
> Win rate alone is **NOT** strategy success rate. A strategy with an 80% win rate can lose money if average losses exceed average gains. SwingLens reports comprehensive metrics including **Net Profit**, **Profit Factor**, **Expectancy**, **Max Drawdown**, **Sharpe Ratio**, and **Sortino Ratio**.

---

## Config & Result Models

### `BacktestConfig`
- `initial_capital`: `100,000.0`
- `position_size_type`: `"fixed"` (allocation %) or `"risk"` (portfolio risk %)
- `position_size_value`: `0.10` (10% allocation or 1% portfolio risk)
- `max_positions`: `5`
- `commission_pct`: `0.001` (0.1% per leg)
- `slippage_pct`: `0.0005` (0.05% per leg)
- `entry_execution`: `"next_open"`
- `ambiguity_policy`: `"conservative"`

### `Trade` Model
- `trade_id`, `symbol`, `strategy_name`, `strategy_version`
- `entry_date`, `entry_price`, `exit_date`, `exit_price`, `quantity`
- `stop_loss`, `target_price`, `gross_pnl`, `transaction_cost`, `slippage_cost`, `net_pnl`, `return_percent`, `holding_period`
- `exit_reason`: `STOP_LOSS` | `TARGET` | `SIGNAL` | `END_OF_BACKTEST`

### `BacktestResult` Model
- Summary metrics: `initial_capital`, `final_capital`, `total_return_pct`, `cagr_pct`, `total_trades`, `winning_trades`, `losing_trades`, `win_rate_pct`, `profit_factor`, `max_drawdown_pct`, `expectancy`, `avg_holding_period`, `sharpe_ratio`, `sortino_ratio`
- `trades`: List of `Trade` records
- `equity_curve`: Daily records list (`date`, `cash`, `equity`, `drawdown`, `drawdown_percent`)
- `warnings`: Warning strings list

---

## Commands & Testing

Run all 65 unit tests:
```bash
PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests
```
