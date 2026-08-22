import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from backend.backtest import BacktestEngine, BacktestResult
from backend.database.connection import get_db_connection
from backend.indicators import calculate_indicators
from backend.indicators.engine import get_price_history
from backend.scanner import MarketScanner, ScanSummary
from backend.scanner.daily_workflow import get_daily_scan_status, run_daily_scan_workflow
from backend.strategies.registry import _GLOBAL_REGISTRY, get_strategy, list_strategies

logger = logging.getLogger(__name__)


class StockHistoryCandle(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    ema200: Optional[float] = None


class StockHistoryResponse(BaseModel):
    symbol: str
    data: List[StockHistoryCandle]


class DailyScanStatusResponse(BaseModel):
    scan_date: str
    already_completed: bool
    status: str
    latest_market_date: Optional[str] = None
    last_completed_at: Optional[str] = None
    buy_count: int = 0
    watch_count: int = 0
    hold_count: int = 0
    skipped_count: int = 0
    error_message: Optional[str] = None


app = FastAPI(
    title="SwingLens API",
    description="Backend API service for SwingLens market scanner and quantitative strategies.",
    version="1.0.0",
)

# Configure CORS middleware for development frontend integration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/daily-scan/status", response_model=DailyScanStatusResponse)
def get_daily_scan_status_endpoint(
    universe: str = Query(default="NIFTY_NEXT_50", description="Index universe name"),
    strategy: str = Query(default="ema_pullback", description="Strategy name"),
):
    """
    Determines whether today's daily market scan workflow has completed successfully.
    """
    try:
        status_data = get_daily_scan_status(universe=universe, strategy=strategy)
        return status_data
    except Exception as e:
        logger.error(f"Error checking daily scan status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/daily-scan/run", response_model=ScanSummary)
def run_daily_scan_endpoint(
    force: bool = Query(default=False, description="Force re-execution of daily scan workflow"),
    universe: str = Query(default="NIFTY_NEXT_50", description="Index universe name"),
    strategy: str = Query(default="ema_pullback", description="Strategy name"),
):
    """
    Executes the daily market scan workflow idempotently.
    If force=False and today's scan is already COMPLETED, returns existing results immediately.
    """
    try:
        summary = run_daily_scan_workflow(universe=universe, strategy=strategy, force=force)
        return summary
    except RuntimeError as rerr:
        raise HTTPException(status_code=409, detail=str(rerr))
    except Exception as e:
        logger.error(f"Error running daily scan workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scanner/latest", response_model=ScanSummary)
def get_latest_scan(
    strategy: str = Query(default="ema_pullback", description="Strategy identifier string"),
    index: str = Query(default="NIFTY_NEXT_50", description="Index universe name"),
):
    """
    Executes the MarketScanner over the specified index using the chosen strategy
    and returns structured scan results for the latest completed daily candle.
    """
    registered_names = _GLOBAL_REGISTRY.list_names()
    normalized_strategy = strategy.lower().strip().replace(" ", "_")

    if normalized_strategy not in registered_names and strategy not in registered_names:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy '{strategy}'. Registered strategies: {registered_names}",
        )

    try:
        scanner = MarketScanner()
        summary = scanner.scan_summary(index_name=index, strategy_name=strategy)
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing scanner API: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to execute daily market scan due to internal server or database error.",
        )


@app.get("/api/backtest/{symbol}", response_model=BacktestResult)
def backtest_single_stock(
    symbol: str,
    strategy: str = Query(default="ema_pullback", description="Strategy identifier string"),
    start_date: str = Query(default=None, description="Optional start date (YYYY-MM-DD)"),
    end_date: str = Query(default=None, description="Optional end date (YYYY-MM-DD)"),
):
    """
    Executes an on-demand single-stock backtest for the specified symbol.
    Queries ONLY that stock's price history from SQLite and runs historical simulation.
    """
    symbol_clean = symbol.strip().upper()
    try:
        strat_obj = get_strategy(strategy)
    except KeyError:
        registered = [s["name"] for s in list_strategies()]
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy '{strategy}'. Registered strategies: {registered}",
        )

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM stocks WHERE symbol = ?", (symbol_clean,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Stock symbol '{symbol_clean}' not found in database.",
            )

        df = get_price_history(conn, symbol_clean, start_date=start_date, end_date=end_date)
    finally:
        conn.close()

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No price history found for symbol '{symbol_clean}' in database.",
        )

    df["symbol"] = symbol_clean
    engine = BacktestEngine(strategy=strat_obj)
    result = engine.run(df)
    return result


@app.get("/api/stocks/{symbol}/history", response_model=StockHistoryResponse)
def get_stock_history(
    symbol: str,
    days: Optional[int] = Query(default=None, description="Number of recent trading sessions to return (e.g. 250)"),
):
    """
    Retrieves historical daily price candles for the specified stock along with EMA20, EMA50, and EMA200 values.
    Queries ONLY local SQLite daily_prices and calculates indicators in-memory without mutating the database.
    """
    symbol_clean = symbol.strip().upper()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM stocks WHERE symbol = ?", (symbol_clean,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Stock symbol '{symbol_clean}' not found in database.",
            )

        df = get_price_history(conn, symbol_clean)
    finally:
        conn.close()

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No price history found for symbol '{symbol_clean}' in database.",
        )

    # Compute indicators over full dataset for indicator calculation accuracy
    df = calculate_indicators(df, ["ema_20", "ema_50", "ema_200"])

    if days and days > 0:
        df_slice = df.tail(days).reset_index(drop=True)
    else:
        df_slice = df

    data_candles: List[StockHistoryCandle] = []
    for _, r in df_slice.iterrows():
        ema20_val = round(float(r["ema_20"]), 2) if "ema_20" in r and pd.notna(r["ema_20"]) else None
        ema50_val = round(float(r["ema_50"]), 2) if "ema_50" in r and pd.notna(r["ema_50"]) else None
        ema200_val = round(float(r["ema_200"]), 2) if "ema_200" in r and pd.notna(r["ema_200"]) else None

        data_candles.append(
            StockHistoryCandle(
                date=str(r["trade_date"]),
                open=round(float(r["open"]), 2),
                high=round(float(r["high"]), 2),
                low=round(float(r["low"]), 2),
                close=round(float(r["close"]), 2),
                volume=int(r["volume"]),
                ema20=ema20_val,
                ema50=ema50_val,
                ema200=ema200_val,
            )
        )

    return StockHistoryResponse(symbol=symbol_clean, data=data_candles)
