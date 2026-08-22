import uuid
from typing import Any, Dict, List, Optional
from .costs import calculate_execution_price, calculate_transaction_costs
from .models import BacktestConfig, ExitReason, Trade


class Position:
    """
    Represents an open trading position in the portfolio.
    """
    def __init__(
        self,
        symbol: str,
        strategy_name: str,
        strategy_version: str,
        entry_date: str,
        entry_price: float,
        quantity: int,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None,
        entry_cost: float = 0.0,
        entry_slippage: float = 0.0,
        signal_date: str = "",
    ):
        self.position_id = str(uuid.uuid4())[:8]
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.strategy_version = strategy_version
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss = stop_loss
        self.target_price = target_price
        self.entry_cost = entry_cost
        self.entry_slippage = entry_slippage
        self.signal_date = signal_date or entry_date


class Portfolio:
    """
    Simulates portfolio cash, positions, trades, and daily equity curve.
    """
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.initial_capital = config.initial_capital
        self.cash = config.initial_capital
        self.open_positions: Dict[str, Position] = {}
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.peak_equity = config.initial_capital

    def get_equity(self, current_prices: Dict[str, float]) -> float:
        """
        Calculates total equity = cash + mark-to-market value of open positions.
        """
        pos_value = 0.0
        for symbol, pos in self.open_positions.items():
            price = current_prices.get(symbol, pos.entry_price)
            pos_value += pos.quantity * price
        return self.cash + pos_value

    def can_open_position(self, symbol: str) -> bool:
        """
        Checks if portfolio allows opening a new position for symbol.
        """
        if symbol in self.open_positions:
            return False
        if len(self.open_positions) >= self.config.max_positions:
            return False
        if self.cash <= 0:
            return False
        return True

    def calculate_quantity(
        self,
        entry_price: float,
        stop_loss: Optional[float],
        current_equity: float,
    ) -> int:
        """
        Calculates position quantity based on configured position sizing strategy.
        - 'fixed': Allocates fixed % of equity.
        - 'risk': Allocates quantity such that max risk = fixed % of equity.
        """
        if entry_price <= 0:
            return 0

        max_alloc_per_pos = current_equity / max(1, self.config.max_positions)
        available_cash = min(self.cash, max_alloc_per_pos)

        if self.config.position_size_type == "risk" and stop_loss and stop_loss > 0 and stop_loss < entry_price:
            risk_amount = current_equity * self.config.position_size_value
            per_share_risk = abs(entry_price - stop_loss)
            raw_qty = int(risk_amount / per_share_risk)
        else:
            # Fixed allocation %
            alloc_amount = current_equity * self.config.position_size_value
            target_amount = min(alloc_amount, available_cash)
            raw_qty = int(target_amount / entry_price)

        # Cap by available cash
        max_possible_qty = int(available_cash / (entry_price * (1.0 + self.config.commission_pct + self.config.slippage_pct)))
        return max(0, min(raw_qty, max_possible_qty))

    def open_position(
        self,
        symbol: str,
        strategy_name: str,
        strategy_version: str,
        entry_date: str,
        raw_price: float,
        quantity: int,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None,
        signal_date: str = "",
    ) -> Optional[Position]:
        """
        Executes buy entry order, applies slippage & transaction costs, and records position.
        """
        if quantity <= 0:
            return None

        exec_price = calculate_execution_price(raw_price, is_buy=True, slippage_pct=self.config.slippage_pct)
        slippage_cost = (exec_price - raw_price) * quantity
        trade_val = exec_price * quantity
        trans_cost = calculate_transaction_costs(trade_val, self.config.commission_pct, self.config.transaction_cost_pct)

        total_outlay = trade_val + trans_cost

        if self.cash < total_outlay:
            # Scale down if slight mismatch
            quantity = int((self.cash - trans_cost) / exec_price)
            if quantity <= 0:
                return None
            trade_val = exec_price * quantity
            slippage_cost = (exec_price - raw_price) * quantity
            trans_cost = calculate_transaction_costs(trade_val, self.config.commission_pct, self.config.transaction_cost_pct)
            total_outlay = trade_val + trans_cost

        self.cash -= total_outlay

        pos = Position(
            symbol=symbol,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            entry_date=entry_date,
            entry_price=exec_price,
            quantity=quantity,
            stop_loss=stop_loss,
            target_price=target_price,
            entry_cost=trans_cost,
            entry_slippage=slippage_cost,
            signal_date=signal_date or entry_date,
        )
        self.open_positions[symbol] = pos
        return pos

    def close_position(
        self,
        symbol: str,
        exit_date: str,
        raw_price: float,
        exit_reason: str,
        holding_period: int = 1,
    ) -> Optional[Trade]:
        """
        Executes sell exit order, applies slippage & costs, credits cash, and records completed Trade.
        """
        if symbol not in self.open_positions:
            return None

        pos = self.open_positions.pop(symbol)
        exec_price = calculate_execution_price(raw_price, is_buy=False, slippage_pct=self.config.slippage_pct)
        exit_slippage = (raw_price - exec_price) * pos.quantity
        trade_val = exec_price * pos.quantity
        exit_cost = calculate_transaction_costs(trade_val, self.config.commission_pct, self.config.transaction_cost_pct)

        net_proceeds = trade_val - exit_cost
        self.cash += net_proceeds

        total_trans_cost = pos.entry_cost + exit_cost
        total_slippage_cost = pos.entry_slippage + exit_slippage
        gross_pnl = (exec_price - pos.entry_price) * pos.quantity
        net_pnl = gross_pnl - total_trans_cost

        pnl_points = round(exec_price - pos.entry_price, 2)
        pnl_percent = round(((exec_price - pos.entry_price) / pos.entry_price) * 100.0, 2)

        r_mult = None
        if pos.stop_loss is not None and abs(pos.entry_price - pos.stop_loss) > 1e-4:
            r_mult = round((exec_price - pos.entry_price) / abs(pos.entry_price - pos.stop_loss), 2)

        cost_basis = (pos.entry_price * pos.quantity) + pos.entry_cost
        return_pct = (net_pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

        h_days = max(1, holding_period)

        trade = Trade(
            trade_id=pos.position_id,
            symbol=symbol,
            strategy_name=pos.strategy_name,
            strategy_version=pos.strategy_version,
            signal_date=pos.signal_date,
            entry_date=pos.entry_date,
            entry_price=round(pos.entry_price, 2),
            exit_date=exit_date,
            exit_price=round(exec_price, 2),
            quantity=pos.quantity,
            stop_loss=round(pos.stop_loss, 2) if pos.stop_loss else None,
            target_price=round(pos.target_price, 2) if pos.target_price else None,
            gross_pnl=round(gross_pnl, 2),
            transaction_cost=round(total_trans_cost, 2),
            slippage_cost=round(total_slippage_cost, 2),
            net_pnl=round(net_pnl, 2),
            pnl_points=pnl_points,
            pnl_percent=pnl_percent,
            return_percent=round(return_pct, 2),
            r_multiple=r_mult,
            holding_period=h_days,
            holding_days=h_days,
            exit_reason=exit_reason,
            status="CLOSED",
        )
        self.closed_trades.append(trade)
        return trade

    def record_daily_equity(self, date_str: str, current_prices: Dict[str, float]) -> None:
        """
        Records daily equity curve state (cash, equity, drawdown, drawdown_pct).
        """
        equity = self.get_equity(current_prices)
        if equity > self.peak_equity:
            self.peak_equity = equity

        drawdown = max(0.0, self.peak_equity - equity)
        drawdown_pct = (drawdown / self.peak_equity * 100.0) if self.peak_equity > 0 else 0.0

        self.equity_curve.append({
            "date": date_str,
            "cash": round(self.cash, 2),
            "equity": round(equity, 2),
            "drawdown": round(drawdown, 2),
            "drawdown_percent": round(drawdown_pct, 2),
        })
