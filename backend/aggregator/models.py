"""
Pydantic data models for the Multi-Strategy Signal Aggregator.

These models are read-only output structures. They do not modify or
extend any individual strategy model.
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AggregatedSignalStrength(str, Enum):
    """
    Named strength classification based on the number of strategies that
    produced a BUY signal on a given stock and date.

    Scoring rules (transparent, deterministic):
        BUY  → 1 point per strategy
        HOLD / SELL / WATCH → 0 points
        ERROR / skipped strategy → excluded from evaluation entirely

    Thresholds:
        0–1 → NO_SIGNAL
        2   → WEAK
        3   → MODERATE
        4   → STRONG
        5   → VERY_STRONG
    """
    NO_SIGNAL = "NO_SIGNAL"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


def score_to_strength(score: int) -> AggregatedSignalStrength:
    """Maps a raw BUY-count score to a named strength level."""
    if score >= 5:
        return AggregatedSignalStrength.VERY_STRONG
    elif score == 4:
        return AggregatedSignalStrength.STRONG
    elif score == 3:
        return AggregatedSignalStrength.MODERATE
    elif score == 2:
        return AggregatedSignalStrength.WEAK
    else:
        return AggregatedSignalStrength.NO_SIGNAL


class StrategyVote(BaseModel):
    """
    The signal cast by a single strategy for a given stock and date.
    One vote per strategy in the aggregation run.
    """
    strategy_name: str
    strategy_version: str
    signal: str  # BUY / HOLD / SELL / WATCH / ERROR
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    risk_reward: Optional[float] = None
    reason: Optional[str] = None
    error: Optional[str] = Field(default=None, description="Set when this strategy raised an exception")


class AggregatedSignalResult(BaseModel):
    """
    Deterministic combined result produced by the SignalAggregator for a
    single stock on the most recent completed trading date.

    Design constraints:
    - score = raw BUY count (integer; no weights, no ML, no probabilities)
    - strength = named label derived purely from score thresholds
    - Individual strategy outputs are never modified
    - Strategies that raise exceptions are excluded from both numerator
      and denominator; strategies_evaluated reflects only clean evaluations
    """
    symbol: str
    signal_date: Optional[str] = None

    # Evaluation metadata
    strategies_evaluated: int = Field(description="Number of strategies that ran without error")
    strategies_total: int = Field(description="Total strategies attempted")

    # Aggregate vote tallies
    buy_count: int
    hold_count: int

    # Score and strength
    score: int = Field(description="Raw BUY count (0–strategies_evaluated)")
    strength: AggregatedSignalStrength

    # Named strategy breakdowns
    buy_strategies: List[str] = Field(
        default_factory=list,
        description="Names of strategies that returned BUY",
    )
    hold_strategies: List[str] = Field(
        default_factory=list,
        description="Names of strategies that returned HOLD, SELL, or WATCH",
    )
    error_strategies: List[str] = Field(
        default_factory=list,
        description="Names of strategies that raised exceptions during evaluation",
    )

    # Representative trade parameters from the first BUY-voting strategy (alphabetically by key)
    # None when no strategy produced a BUY signal.
    best_entry_price: Optional[float] = Field(
        default=None,
        description="Entry price from the first BUY-voting strategy (by registry key order)",
    )
    best_stop_loss: Optional[float] = Field(
        default=None,
        description="Stop loss from the first BUY-voting strategy",
    )
    best_target_price: Optional[float] = Field(
        default=None,
        description="Target price from the first BUY-voting strategy",
    )
    best_risk_reward: Optional[float] = Field(
        default=None,
        description="Risk-reward ratio from the first BUY-voting strategy",
    )
    best_strategy_name: Optional[str] = Field(
        default=None,
        description="Name of the strategy that provided the best_* trade parameters",
    )

    # Full per-strategy breakdown (one entry per attempted strategy)
    votes: List[StrategyVote] = Field(
        default_factory=list,
        description="Detailed per-strategy vote breakdown",
    )

    metadata: Dict[str, Any] = Field(default_factory=dict)
