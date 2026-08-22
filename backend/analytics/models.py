"""
Pydantic data models for Strategy Historical Quality Analytics.

Provides transparent, deterministic metrics and quality classifications
for trading strategies based on empirical historical backtest performance.
"""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class StrategyQualityClassification(str, Enum):
    """
    Transparent, deterministic classification of historical strategy performance.

    Thresholds:
    - INSUFFICIENT_DATA: total_trades < 10 (sample size too small for statistical evaluation)
    - POSITIVE: total_trades >= 10, total_r > 0, profit_factor >= 1.0, and average_r > 0
    - NEGATIVE: total_trades >= 10, total_r < 0, profit_factor < 1.0, and average_r < 0
    - NEUTRAL:  total_trades >= 10, does not meet all POSITIVE or all NEGATIVE conditions
    """
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class StrategyStockMetrics(BaseModel):
    """
    Historical performance metrics for a single strategy on a specific stock.
    """
    symbol: str
    trades: int = Field(description="Total completed trades")
    wins: int = Field(description="Number of winning trades (net_pnl > 0)")
    losses: int = Field(description="Number of losing trades (net_pnl <= 0)")
    win_rate: float = Field(description="Win rate percentage (0.0 to 100.0)")
    average_r: float = Field(description="Average R-multiple across trades with defined risk")
    total_r: float = Field(description="Total accumulated R-multiples")
    profit_factor: float = Field(description="Gross profit divided by gross loss")
    max_drawdown: float = Field(description="Maximum peak-to-trough drawdown percentage")
    average_holding_days: float = Field(description="Average holding duration in trading days")
    target_hit_rate: float = Field(description="Percentage of trades that exited at profit target")
    stop_hit_rate: float = Field(description="Percentage of trades that exited at stop loss")
    ambiguous_rate: float = Field(description="Percentage of trades with ambiguous same-candle target & stop touch")
    average_mfe_r: float = Field(description="Average Maximum Favorable Excursion in R-multiples")
    average_mae_r: float = Field(description="Average Maximum Adverse Excursion in R-multiples")


class StrategyQualityMetrics(BaseModel):
    """
    Aggregated historical quality metrics and classification for a trading strategy.
    """
    strategy_name: str
    strategy_version: str
    classification: StrategyQualityClassification
    classification_reason: str = Field(description="Human-readable explanation of deterministic classification rule")
    trades: int = Field(description="Total completed trades across tested stocks")
    wins: int = Field(description="Total winning trades")
    losses: int = Field(description="Total losing trades")
    win_rate: float = Field(description="Win rate percentage (0.0 to 100.0)")
    average_r: float = Field(description="Average R-multiple across all trades with defined risk")
    total_r: float = Field(description="Total accumulated R-multiples across all trades")
    profit_factor: float = Field(description="Gross profit divided by gross loss across all trades")
    max_drawdown: float = Field(description="Worst maximum drawdown percentage observed across tested stocks")
    average_holding_days: float = Field(description="Average holding duration in trading days")
    target_hit_rate: float = Field(description="Percentage of trades that exited at profit target (0.0 to 100.0)")
    stop_hit_rate: float = Field(description="Percentage of trades that exited at stop loss (0.0 to 100.0)")
    ambiguous_rate: float = Field(description="Percentage of trades with ambiguous same-candle target & stop touch (0.0 to 100.0)")
    average_mfe_r: float = Field(description="Average Maximum Favorable Excursion in R-multiples")
    average_mae_r: float = Field(description="Average Maximum Adverse Excursion in R-multiples")
    stocks_tested: int = Field(description="Number of stock symbols evaluated")
    per_stock: Optional[Dict[str, StrategyStockMetrics]] = Field(
        default=None,
        description="Optional breakdown of metrics per evaluated stock",
    )


class StrategyAnalyticsResponse(BaseModel):
    """
    Top-level response model for strategy historical quality analytics.
    """
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    symbols: List[str] = Field(description="Symbols evaluated in this analytics run")
    strategies: List[StrategyQualityMetrics] = Field(description="Quality metrics for each evaluated strategy")
