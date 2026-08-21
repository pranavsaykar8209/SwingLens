from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ScanSignalType(str, Enum):
    BUY = "BUY"
    WATCH = "WATCH"
    HOLD = "HOLD"
    ERROR = "ERROR"


class ScanResult(BaseModel):
    """
    Structured scan result for an individual stock evaluated by a strategy.
    Designed for easy FastAPI serialization and consumption by React UI.
    """
    symbol: str
    company_name: Optional[str] = None
    signal: ScanSignalType
    signal_date: Optional[str] = None
    close: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    risk_reward: Optional[float] = None
    score: Optional[float] = Field(default=None, description="Confidence score from strategy if available")
    strategy_name: str
    strategy_version: str
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    status: str = "SUCCESS"


class ScanSummary(BaseModel):
    """
    Structured summary of a complete universe scan run.
    Uses populate_by_name=True to support both stocks_scanned/scanned_count and skip_count/error_count.
    """
    model_config = ConfigDict(populate_by_name=True)

    scan_date: str
    universe: str
    strategy: str
    strategy_version: str
    stocks_scanned: int = Field(validation_alias="scanned_count", default=0)
    buy_count: int = 0
    watch_count: int = 0
    hold_count: int = 0
    skip_count: int = Field(validation_alias="error_count", default=0)
    results: List[ScanResult] = Field(default_factory=list)

    @property
    def scanned_count(self) -> int:
        return self.stocks_scanned

    @property
    def error_count(self) -> int:
        return self.skip_count
