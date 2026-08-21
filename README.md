# SwingLens

## Description
SwingLens is a monorepo application structured with a React frontend, a FastAPI backend, a market-data ingestion engine for Indian equities, and point-in-time index constituent tracking.

## Technology Stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, ESLint
- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic
- **Market Data & Storage:** SQLite, yfinance, pandas, httpx
- **Testing:** Pytest

---

## Market Data & Index Membership Architecture

SwingLens decouples price history ingestion from index constituent membership tracking to support accurate point-in-time querying.

```
backend/
├── database/
│   └── connection.py       # SQLite connection manager, schema & is_index_member helper
├── market_data/
│   ├── universe.py         # Nifty Next 50 constituent loader (NSE URL + fallback)
│   ├── downloader.py       # yfinance daily historical fetcher & concurrent downloader
│   ├── membership.py       # Point-in-time index membership update manager
│   └── validator.py        # OHLCV data validation (NaN checks, High/Low relationship)
└── scripts/
    ├── initialize_data.py   # Full 5-year historical daily price initialization CLI
    ├── update_market_data.py# Incremental daily price update CLI
    ├── update_index_membership.py # CLI command to update index membership tracking
    └── data_quality_report.py  # Read-only database quality audit CLI
```

---

## Database Location & Schema

- **Database Path:** `data/swinglens.db` *(Excluded from Git repository)*

### Table: `stocks`
Stores equity metadata and active status.
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `symbol` (TEXT NOT NULL UNIQUE)
- `ticker` (TEXT NOT NULL UNIQUE)
- `company_name` (TEXT)
- `exchange` (TEXT)
- `series` (TEXT)
- `is_active` (INTEGER NOT NULL DEFAULT 1)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### Table: `daily_prices`
Stores historical daily OHLCV candlestick records.
- `stock_id` (INTEGER NOT NULL, FK -> `stocks.id`)
- `trade_date` (DATE NOT NULL)
- `open` (REAL), `high` (REAL), `low` (REAL), `close` (REAL), `adjusted_close` (REAL), `volume` (INTEGER)
- `created_at` (DATETIME)
- **PRIMARY KEY:** `(stock_id, trade_date)`

### Table: `index_memberships`
Stores point-in-time index constituent membership validity windows.
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `index_name` (TEXT NOT NULL) - e.g. `NIFTY_NEXT_50`
- `stock_id` (INTEGER NOT NULL, FK -> `stocks.id`)
- `valid_from` (DATE NOT NULL) - Start date of membership window
- `valid_to` (DATE NULL) - End date of membership window (`NULL` if currently active)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)
- **UNIQUE:** `(index_name, stock_id, valid_from)`

### Indexes
- `idx_stocks_symbol` ON `stocks(symbol)`
- `idx_stocks_ticker` ON `stocks(ticker)`
- `idx_daily_prices_stock_id` ON `daily_prices(stock_id)`
- `idx_daily_prices_trade_date` ON `daily_prices(trade_date)`
- `idx_daily_prices_stock_date` ON `daily_prices(stock_id, trade_date)`
- `idx_index_memberships_index_name` ON `index_memberships(index_name)`
- `idx_index_memberships_stock_id` ON `index_memberships(stock_id)`
- `idx_index_memberships_valid_from` ON `index_memberships(valid_from)`
- `idx_index_memberships_valid_to` ON `index_memberships(valid_to)`
- `idx_index_memberships_lookup` ON `index_memberships(index_name, valid_from, valid_to)`

---

## Index Membership & Point-in-Time Querying

### Why Index Membership is Stored Separately
Applying today's Nifty Next 50 constituent list retrospectively to 5-year historical price data introduces severe **survivorship bias**. Stocks that performed poorly or were demoted in past years would be omitted from historical backtests, skewing strategy performance.

By storing membership ranges in `index_memberships` with `valid_from` and `valid_to` dates:
1. Current constituents are recorded starting from today's date (`valid_to = NULL`).
2. We do not invent historical membership dates for newly added constituents.
3. Historical constituent change logs will be populated prior to backtesting to enable realistic point-in-time backtesting.

### Querying Membership Status
Use the database helper function `is_index_member`:
```python
from backend.database.connection import get_db_connection, is_index_member

conn = get_db_connection()
is_active = is_index_member(conn, index_name="NIFTY_NEXT_50", stock_id=1, trade_date="2024-05-20")
```

---

## Commands for Local Setup

### 1. Set Up Environment
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 2. Initialize Market Prices (5-Year Historical Download)
```bash
PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.initialize_data
```

### 3. Update Index Membership Records
```bash
PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.update_index_membership
```

### 4. Run Incremental Daily Price Update
```bash
PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.update_market_data
```

### 5. Run Data Quality Audit
```bash
PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.data_quality_report
```

---

## Development & Testing

Run all unit tests:
```bash
PYTHONPATH=. backend/.venv/bin/pytest backend/tests
```
