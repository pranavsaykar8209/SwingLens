# SwingLens

## Description
SwingLens is a monorepo application structured with a React frontend, a FastAPI backend, a market-data ingestion engine for Indian equities, point-in-time index constituent tracking, and a reusable technical indicator engine.

## Technology Stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, ESLint
- **Backend:** Python 3.12+, FastAPI, Uvicorn, Pydantic
- **Market Data & Storage:** SQLite, yfinance, pandas, numpy, httpx
- **Testing:** Pytest

---

## Technical Indicator Engine Architecture

The **Technical Indicator Engine** operates as a pure, in-memory analytical layer decoupled from database storage and strategy execution.

```
backend/
├── indicators/
│   ├── __init__.py         # Package exports
│   ├── ema.py              # EMA & SMA calculations for arbitrary periods
│   ├── rsi.py              # Wilder-style RSI calculation
│   ├── atr.py              # True Range (TR) & Wilder-style smoothed ATR
│   ├── volume.py           # Volume SMA & Relative Volume (RVOL)
│   ├── price_action.py     # % Change, distance from EMA, rolling High/Low, crossovers
│   └── engine.py           # Price history loader & analytical calculate_indicators() API
```

### Clean Raw Data Guarantee
- The SQLite table `daily_prices` contains **ONLY** raw OHLCV market data (`open`, `high`, `low`, `close`, `adjusted_close`, `volume`).
- Calculated indicator columns (e.g. `ema_20`, `rsi_14`) exist **strictly in-memory** during DataFrame analysis and are **never** written back into SQLite.

### Strict No Look-Ahead Guarantee
- Indicators consume ONLY data available on or before the current candle.
- Mathematical transformations rely strictly on historical windowing (`rolling`, `ewm`, `shift`), preventing future price leakage in backtests.

### Warm-Up Period Rules
- Indicators require a sufficient historical candle warm-up period (e.g., `EMA 200` requires at least 200 prior observations, `RSI 14` requires 14 prior observations).
- Warm-up periods return `NaN` (unrounded `float64`) and are **never** silently replaced with zero.

---

## Supported Technical Indicators & Primitives

| Indicator / Primitive | Module | Function / Key Syntax | Description |
| :--- | :--- | :--- | :--- |
| **EMA** | `ema.py` | `calculate_ema(series, period)` / `"ema_<period>"` | Exponential Moving Average (supports arbitrary periods) |
| **SMA** | `ema.py` | `calculate_sma(series, period)` / `"sma_<period>"` | Simple Moving Average (supports arbitrary periods) |
| **RSI** | `rsi.py` | `calculate_rsi(series, period=14)` / `"rsi_14"` | Wilder-style Relative Strength Index |
| **TR & ATR** | `atr.py` | `calculate_atr(high, low, close, period=14)` / `"atr_14"` | True Range & Wilder-style smoothed Average True Range |
| **Volume SMA** | `volume.py` | `calculate_volume_sma(volume, period=20)` / `"volume_sma_20"` | Volume moving average |
| **Relative Volume** | `volume.py` | `calculate_relative_volume(volume, period=20)` / `"relative_volume_20"` | Current Volume / Volume SMA |
| **Distance from EMA** | `price_action.py` | `distance_from_ema_pct(close, ema)` / `"dist_ema_<period>_pct"` | % distance of close price from EMA |
| **% Change** | `price_action.py` | `percentage_change(series, periods=1)` / `"pct_change_<periods>"` | Multi-period percentage change |
| **Rolling High/Low** | `price_action.py` | `highest_high`, `lowest_low` / `"highest_high_<period>"` | Rolling highest high & lowest low |
| **Crossovers** | `price_action.py` | `crossed_above(series_a, series_b)`, `crossed_below` | Returns `True` **only** on the exact candle of crossing |

---

## Example Usage

### 1. High-Level Indicator Engine API
```python
from backend.database.connection import get_db_connection
from backend.indicators import get_price_history, calculate_indicators

conn = get_db_connection()

# Fetch raw OHLCV DataFrame for a stock
df = get_price_history(conn, symbol="COALINDIA")

# Compute analytical indicators in-memory
df_analyzed = calculate_indicators(
    df,
    indicators=[
        "ema_20",
        "ema_50",
        "ema_200",
        "rsi_14",
        "atr_14",
        "volume_sma_20",
        "relative_volume_20",
        "dist_ema_20_pct",
    ]
)
```

---

## Database Location & Schema

- **Database Path:** `data/swinglens.db` *(Excluded from Git repository)*

### Tables: `stocks`, `daily_prices`, `index_memberships`
*(See earlier schema documentation; `daily_prices` remains strictly raw OHLCV data).*

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

### 2. Initialize Market Data
```bash
PYTHONPATH=. backend/.venv/bin/python -m backend.scripts.initialize_data
```

### 3. Run All Tests
```bash
PYTHONPATH=. backend/.venv/bin/python -m pytest backend/tests
```
