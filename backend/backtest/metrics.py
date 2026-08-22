from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np

from .models import Trade


def calculate_performance_metrics(
    initial_capital: float,
    final_capital: float,
    closed_trades: List[Trade],
    equity_curve: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
    open_trades: int = 0,
) -> Dict[str, Any]:
    """
    Computes statistical and portfolio performance metrics for a single-stock backtest run.
    """
    total_trades = len(closed_trades)
    winning_trades = [t for t in closed_trades if (t.pnl_points > 0 or t.net_pnl > 0)]
    losing_trades = [t for t in closed_trades if (t.pnl_points < 0 or t.net_pnl < 0)]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)

    win_rate_pct = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

    total_return_dollar = final_capital - initial_capital
    total_return_pct = (total_return_dollar / initial_capital * 100.0) if initial_capital > 0 else 0.0

    # CAGR Calculation
    cagr_pct = 0.0
    try:
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date, "%Y-%m-%d")
        years = (d2 - d1).days / 365.25
        if years >= 0.25 and initial_capital > 0 and final_capital > 0:
            cagr_pct = ((final_capital / initial_capital) ** (1.0 / years) - 1.0) * 100.0
    except Exception:
        cagr_pct = 0.0

    # Trade PnL & percentage metrics
    win_pcts = [t.pnl_percent for t in winning_trades]
    loss_pcts = [t.pnl_percent for t in losing_trades]
    all_pcts = [t.pnl_percent for t in closed_trades]

    avg_win_pct = (sum(win_pcts) / win_count) if win_count > 0 else 0.0
    avg_loss_pct = (sum(loss_pcts) / loss_count) if loss_count > 0 else 0.0
    avg_trade_pct = (sum(all_pcts) / total_trades) if total_trades > 0 else 0.0

    wins = [t.net_pnl for t in winning_trades]
    losses = [abs(t.net_pnl) for t in losing_trades]

    gross_profit = sum(wins) if wins else sum(t.pnl_points for t in winning_trades if t.pnl_points > 0)
    gross_loss = sum(losses) if losses else sum(abs(t.pnl_points) for t in losing_trades if t.pnl_points < 0)

    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 2)
    elif gross_profit > 0:
        profit_factor = 999.0
    else:
        profit_factor = 0.0

    avg_win = (gross_profit / win_count) if win_count > 0 else 0.0
    avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0.0
    avg_trade = (total_return_dollar / total_trades) if total_trades > 0 else 0.0

    win_ratio = win_rate_pct / 100.0
    loss_ratio = 1.0 - win_ratio
    expectancy = (win_ratio * avg_win) - (loss_ratio * avg_loss)

    holding_days_list = [t.holding_days if t.holding_days > 0 else t.holding_period for t in closed_trades]
    avg_holding_days = (sum(holding_days_list) / total_trades) if total_trades > 0 else 0.0
    max_holding_days = max(holding_days_list) if holding_days_list else 0

    # R-multiple metrics
    r_multiples = [t.r_multiple for t in closed_trades if t.r_multiple is not None]
    winning_r_list = [t.r_multiple for t in winning_trades if t.r_multiple is not None]
    losing_r_list = [t.r_multiple for t in losing_trades if t.r_multiple is not None]

    total_r = sum(r_multiples) if r_multiples else 0.0
    winning_r = sum(winning_r_list) if winning_r_list else 0.0
    losing_r = sum(losing_r_list) if losing_r_list else 0.0
    avg_r = (total_r / len(r_multiples)) if r_multiples else 0.0

    # Max Drawdown from equity curve
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    if equity_curve:
        max_drawdown = max(r["drawdown"] for r in equity_curve)
        max_drawdown_pct = max(r["drawdown_percent"] for r in equity_curve)

    # Sharpe & Sortino Ratios from daily equity returns
    sharpe_ratio = None
    sortino_ratio = None
    if len(equity_curve) > 5:
        equities = np.array([r["equity"] for r in equity_curve])
        returns = np.diff(equities) / equities[:-1]
        std_returns = np.std(returns)

        if std_returns > 1e-6:
            sharpe_ratio = round(float((np.mean(returns) / std_returns) * np.sqrt(252)), 2)

        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = np.std(downside_returns)
            if downside_std > 1e-6:
                sortino_ratio = round(float((np.mean(returns) / downside_std) * np.sqrt(252)), 2)

    return {
        "initial_capital": round(initial_capital, 2),
        "final_capital": round(final_capital, 2),
        "total_return_pct": round(total_return_pct, 2),
        "cagr_pct": round(cagr_pct, 2),
        "total_trades": total_trades,
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "open_trades": open_trades,
        "win_rate": round(win_rate_pct, 2),
        "win_rate_pct": round(win_rate_pct, 2),
        "average_win_percent": round(avg_win_pct, 2),
        "average_loss_percent": round(avg_loss_pct, 2),
        "average_trade_percent": round(avg_trade_pct, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "net_profit": round(total_return_dollar, 2),
        "profit_factor": profit_factor,
        "avg_trade": round(avg_trade, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "max_drawdown_percent": round(max_drawdown_pct, 2),
        "avg_holding_period": round(avg_holding_days, 1),
        "average_holding_days": round(avg_holding_days, 1),
        "maximum_holding_days": int(max_holding_days),
        "average_r_multiple": round(avg_r, 2),
        "total_r": round(total_r, 2),
        "winning_r": round(winning_r, 2),
        "losing_r": round(losing_r, 2),
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
    }

