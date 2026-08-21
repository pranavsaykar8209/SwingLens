from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TARGET = "TARGET"
    SIGNAL = "SIGNAL"
    END_OF_BACKTEST = "END_OF_BACKTEST"


class BacktestConfig(BaseModel):
    """
    Configuration settings for backtest execution and risk management.
    """
    initial_capital: float = 100000.0
    position_size_type: str = Field(default="fixed", description="'fixed' (capital allocation %) or 'risk' (% of capital risked)")
    position_size_value: float = Field(default=0.10, description="0.10 = 10% fixed allocation or 1% risk")
    max_positions: int = 5
    commission_pct: float = 0.001       # 0.1% per trade leg
    slippage_pct: float = 0.0005        # 0.05% per trade leg
    transaction_cost_pct: float = 0.0
    entry_execution: str = "next_open"  # Signal at candle N close -> entry at candle N+1 open
    exit_execution: str = "next_open"
    ambiguity_policy: str = Field(default="conservative", description="'conservative', 'optimistic', or 'skip'")
    allow_short: bool = False
    timeframe: str = "1d"


class Trade(BaseModel):
    """
    Model representing a completed trade.
    """
    trade_id: str
    symbol: str
    strategy_name: str
    strategy_version: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    quantity: int
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    gross_pnl: float
    transaction_cost: float
    slippage_cost: float
    net_pnl: float
    return_percent: float
    holding_period: int
    exit_reason: str


class BacktestResult(BaseModel):
    """
    Model representing complete backtest performance results and analytical output.
    """
    strategy_name: str
    strategy_version: str
    symbol_or_universe: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    cagr_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    expectancy: float
    avg_holding_period: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    trades: List[Trade] = Field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = Field(default_factory=list)  # date, cash, equity, drawdown, drawdown_pct
    warnings: List[str] = Field(default_factory=list)
