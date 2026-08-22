"""
Pydantic models for the Daily Signal Ranking layer.

These models are read-only output structures, downstream of AggregatedSignalResult.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.aggregator.models import AggregatedSignalStrength


class SignalTier(str, Enum):
    """
    Human-readable classification tier based on signal strength.
    Deliberately avoids the word 'prediction'.
    """
    STRONG_OPPORTUNITY = "STRONG_OPPORTUNITY"      # VERY_STRONG or STRONG
    MODERATE_OPPORTUNITY = "MODERATE_OPPORTUNITY"  # MODERATE
    WEAK_OR_NO_SIGNAL = "WEAK_OR_NO_SIGNAL"        # WEAK or NO_SIGNAL


def strength_to_tier(strength: AggregatedSignalStrength) -> SignalTier:
    """Maps an AggregatedSignalStrength to a SignalTier bucket."""
    if strength in (AggregatedSignalStrength.VERY_STRONG, AggregatedSignalStrength.STRONG):
        return SignalTier.STRONG_OPPORTUNITY
    elif strength == AggregatedSignalStrength.MODERATE:
        return SignalTier.MODERATE_OPPORTUNITY
    else:
        return SignalTier.WEAK_OR_NO_SIGNAL


class RankedSignal(BaseModel):
    """
    Single ranked entry in the Daily Signal Ranking.
    Wraps the core AggregatedSignalResult fields without duplicating the model.
    """
    rank: int = Field(description="Rank position (1 = strongest setup)")
    symbol: str
    company_name: Optional[str] = None
    signal_date: Optional[str] = None

    # Aggregated multi-strategy metrics
    score: int = Field(description="Raw BUY count (0–5)")
    strength: AggregatedSignalStrength
    tier: SignalTier = Field(description="Human-readable signal strength tier")
    buy_count: int
    strategies_evaluated: int
    strategies_total: int

    # Strategy breakdown
    buy_strategies: List[str] = Field(default_factory=list)
    hold_strategies: List[str] = Field(default_factory=list)
    error_strategies: List[str] = Field(default_factory=list)
    best_strategy_name: Optional[str] = None

    # Representative trade parameters from the first BUY-voting strategy
    best_entry_price: Optional[float] = None
    best_stop_loss: Optional[float] = None
    best_target_price: Optional[float] = None
    best_risk_reward: Optional[float] = None


class DailySignalRanking(BaseModel):
    """
    Top-level response model for GET /api/daily-signals.

    Contains overall run metadata and the ranked list of evaluated stocks.
    """
    signal_date: Optional[str] = Field(
        default=None,
        description="The most recent completed daily candle date used for evaluation",
    )
    universe: str = Field(description="Index universe evaluated (e.g. NIFTY_NEXT_50)")
    universe_size: int = Field(description="Total active constituents in universe")
    evaluated_count: int = Field(description="Stocks successfully evaluated (no errors)")
    excluded_count: int = Field(description="Stocks skipped due to insufficient history or errors")
    buy_signal_count: int = Field(description="Stocks with at least 1 BUY signal across strategies")

    # Full ranked results (all successfully evaluated stocks)
    results: List[RankedSignal] = Field(
        default_factory=list,
        description="All successfully evaluated stocks, ranked by multi-strategy agreement (strongest first)",
    )

    # Optional shortlist (populated when limit param is provided)
    shortlist: List[RankedSignal] = Field(
        default_factory=list,
        description="Top-N shortlist (respects the ?limit= parameter)",
    )
