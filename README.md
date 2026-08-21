# SwingLens

## Description
SwingLens is a monorepo application structured with a React frontend, a FastAPI backend, and a robust market-data ingestion engine for Indian equities (Nifty Next 50 universe).

## Technology Stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, ESLint
- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic
- **Market Data & Storage:** SQLite, yfinance, pandas, httpx
- **Testing:** Pytest

---

## Market Data Architecture

SwingLens utilizes an independent market-data ingestion layer decoupled from business, UI, and backtesting logic.

```
backend/
├── database/
│   └── connection.py       # SQLite connection manager & schema initializer
├── market_data/
│   ├── universe.py         # Nifty Next 50 constituent fetcher (NSE URL + fallback)
│   ├── downloader.py       # yfinance daily historical fetcher & concurrent downloader
│   └── validator.py        # OHLCV data validation (NaN checks, High/Low relationship)
└── scripts/
    ├── initialize_data.py   # Full 5-year initialization CLI script
    └── update_market_data.py# Incremental daily update CLI script
```

### Data Source
- **Constituent Universe:** Nifty Next 50 index constituents (fetched dynamically from official NSE endpoints with curated fallback).
- **Historical Data:** Daily OHLCV data fetched via Yahoo Finance (`yfinance`).

---

## Database Location & Schema

- **Database Path:** `data/swinglens.db` *(Excluded from Git repository)*

### Table: `stocks`
Stores equity metadata and active status.
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `symbol` (TEXT NOT NULL UNIQUE) - e.g. `COALINDIA`
- `ticker` (TEXT NOT NULL UNIQUE) - e.g. `COALINDIA.NS`
- `company_name` (TEXT)
- `exchange` (TEXT) - e.g. `NSE`
- `series` (TEXT) - e.g. `EQ`
- `is_active` (INTEGER NOT NULL DEFAULT 1)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### Table: `daily_prices`
Stores historical daily OHLCV candlestick records.
- `stock_id` (INTEGER NOT NULL, FK -> `stocks.id`)
- `trade_date` (DATE NOT NULL) - Format `YYYY-MM-DD`
- `open` (REAL)
- `high` (REAL)
- `low` (REAL)
- `close` (REAL)
- `adjusted_close` (REAL)
- `volume` (INTEGER)
- `created_at` (DATETIME)
- **PRIMARY KEY:** `(stock_id, trade_date)`

### Indexes
- `idx_stocks_symbol` ON `stocks(symbol)`
- `idx_stocks_ticker` ON `stocks(ticker)`
- `idx_daily_prices_stock_id` ON `daily_prices(stock_id)`
- `idx_daily_prices_trade_date` ON `daily_prices(trade_date)`
- `idx_daily_prices_stock_date` ON `daily_prices(stock_id, trade_date)`

---

## Initializing Local Database (For New Users)

When cloning SwingLens for the first time, your local database does not exist because `data/swinglens.db` is ignored in Git. Follow these commands to recreate your local database:

### 1. Set Up Virtual Environment & Install Dependencies
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 2. Run Initial Data Download (5-Year Historical Initialization)
From the repository root:
```bash
PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.initialize_data
```

This will:
1. Create `data/swinglens.db` and initialize tables/indexes.
2. Fetch the current Nifty Next 50 constituents.
3. Download ~5 years of daily OHLCV data for all constituents.
4. Perform non-duplicating `UPSERT` operations into `daily_prices`.

### 3. Run Incremental Daily Updates
To update your local database with new daily price action:
```bash
PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.update_market_data
```

---

## Yahoo Finance & Survivorship Bias Notes

### Data Provider Limitations (yfinance)
- Yahoo Finance data can occasionally exhibit rate limits, adjusted price adjustments, or temporary data gaps.
- The validator filters out bad rows (e.g. `High < Low`, invalid volumes, or missing values) and logs errors without stopping execution.

### Survivorship Bias Warning
> [!WARNING]
> Using the **current** Nifty Next 50 constituent list retrospectively across 5 years of historical data introduces **survivorship bias**. Stocks that were members of the index 3 or 5 years ago but were subsequently demoted or delisted are omitted from the current universe.
> 
> *Historical point-in-time index constituent tracking will be added in a future update to enable institutional-grade backtesting.*

---

## Development & Testing

Run all unit tests (without making live market network calls):
```bash
PYTHONPATH=. backend/.venv/bin/pytest backend/tests
```

---

## Status
Market data ingestion pipeline complete — ready for initial data download.
