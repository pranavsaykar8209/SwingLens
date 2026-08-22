from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TARGET = "TARGET"
    END_OF_DATA = "END_OF_DATA"
    END_OF_BACKTEST = "END_OF_DATA"
    SIGNAL = "SIGNAL"



class BacktestConfig(BaseModel):
    """
    Configuration settings for backtest execution and risk management.
    """
    initial_capital: float = 100000.0
    position_size_type: str = Field(default="fixed", description="'fixed' (capital allocation %) or 'risk' (% of capital risked)")
    position_size_value: float = Field(default=0.10, description="0.10 = 10% fixed allocation or 1% risk")
    max_positions: int = 1
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
    Model representing a completed or open trade.
    """
    trade_id: str = ""
    symbol: str
    strategy_name: str
    strategy_version: str
    signal_date: str = ""
    entry_date: str
    entry_price: float
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    exit_date: str = ""
    exit_price: float = 0.0
    exit_reason: str = ""
    quantity: int = 1
    gross_pnl: float = 0.0
    transaction_cost: float = 0.0
    slippage_cost: float = 0.0
    net_pnl: float = 0.0
    pnl_points: float = 0.0
    pnl_percent: float = 0.0
    return_percent: float = 0.0
    r_multiple: Optional[float] = None
    holding_period: int = 0
    holding_days: int = 0
    status: str = "CLOSED"


class BacktestResult(BaseModel):
    """
    Model representing complete single-stock backtest performance results and analytical output.
    """
    symbol: str
    strategy: str = ""
    strategy_name: str
    strategy_version: str
    symbol_or_universe: str = ""
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    final_capital: float = 100000.0
    total_return_pct: float = 0.0
    cagr_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    open_trades: int = 0
    win_rate: float = 0.0
    win_rate_pct: float = 0.0
    average_win_percent: float = 0.0
    average_loss_percent: float = 0.0
    average_trade_percent: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_percent: float = 0.0
    expectancy: float = 0.0
    avg_holding_period: float = 0.0
    average_holding_days: float = 0.0
    maximum_holding_days: int = 0
    average_r_multiple: float = 0.0
    total_r: float = 0.0
    winning_r: float = 0.0
    losing_r: float = 0.0
    ambiguity_policy_note: str = (
        "Conservative deterministic assumption: If both high >= target and low <= stop_loss occur "
        "on the same daily candle, the exit is recorded at STOP_LOSS."
    )
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    trades: List[Trade] = Field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

