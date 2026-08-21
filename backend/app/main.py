import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.scanner import MarketScanner, ScanSummary
from backend.strategies.registry import _GLOBAL_REGISTRY

logger = logging.getLogger(__name__)

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
