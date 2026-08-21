def calculate_execution_price(price: float, is_buy: bool, slippage_pct: float) -> float:
    """
    Adjusts standard execution price to account for market slippage.

    BUY execution price = price * (1 + slippage_pct)
    SELL execution price = price * (1 - slippage_pct)
    """
    if price <= 0:
        return price

    if is_buy:
        return price * (1.0 + slippage_pct)
    else:
        return price * (1.0 - slippage_pct)


def calculate_transaction_costs(
    trade_value: float, commission_pct: float, transaction_cost_pct: float = 0.0
) -> float:
    """
    Calculates total transaction costs (brokerage, exchange fees, taxes) for a trade leg.

    Total Cost = trade_value * (commission_pct + transaction_cost_pct)
    """
    if trade_value <= 0:
        return 0.0

    return trade_value * (commission_pct + transaction_cost_pct)
