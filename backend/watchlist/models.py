"""Pydantic models for persisted watchlist setup snapshots."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.aggregator.models import AggregatedSignalStrength


class WatchlistStatus(str, Enum):
    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class WatchlistOutcome(str, Enum):
    PENDING = "PENDING"
    ENTRY_REACHED = "ENTRY_REACHED"
    TARGET_HIT = "TARGET_HIT"
    STOP_HIT = "STOP_HIT"
    EXPIRED = "EXPIRED"
    NO_ENTRY = "NO_ENTRY"
    AMBIGUOUS = "AMBIGUOUS"


class WatchlistSetupCreate(BaseModel):
    """Required immutable snapshot fields from an aggregated BUY opportunity."""

    symbol: str = Field(min_length=1)
    signal_date: date
    aggregated_score: int = Field(ge=1, le=5)
    signal_strength: AggregatedSignalStrength
    buy_strategies: list[str] = Field(min_length=1)
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    target_price: float = Field(gt=0)
    risk_reward: float = Field(gt=0)
    best_strategy_name: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value.upper()

    @field_validator("best_strategy_name")
    @classmethod
    def validate_best_strategy_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("buy_strategies")
    @classmethod
    def validate_strategy_names(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("buy_strategies must contain unique, non-blank strategy names")
        return normalized

    @model_validator(mode="after")
    def validate_buy_snapshot(self) -> "WatchlistSetupCreate":
        if self.signal_strength == AggregatedSignalStrength.NO_SIGNAL:
            raise ValueError("NO_SIGNAL setups cannot be added to the watchlist")
        if self.stop_loss >= self.entry_price:
            raise ValueError("stop_loss must be below entry_price for a BUY setup")
        if self.target_price <= self.entry_price:
            raise ValueError("target_price must be above entry_price for a BUY setup")
        return self


class WatchlistStatusUpdate(BaseModel):
    status: WatchlistStatus


class WatchlistSetup(BaseModel):
    id: int
    symbol: str
    company_name: str | None = None
    signal_date: date
    created_at: datetime
    status: WatchlistStatus
    aggregated_score: int
    signal_strength: AggregatedSignalStrength
    buy_strategies: list[str]
    entry_price: float
    stop_loss: float
    target_price: float
    risk_reward: float
    best_strategy_name: str
    outcome: WatchlistOutcome = WatchlistOutcome.PENDING
    entry_date: date | None = None
    exit_date: date | None = None
    exit_price: float | None = None
    holding_days: int | None = None
    mfe: float | None = None
    mfe_r: float | None = None
    mae: float | None = None
    mae_r: float | None = None
    realized_r: float | None = None
    outcome_checked_at: datetime | None = None
