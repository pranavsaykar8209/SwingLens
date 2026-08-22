"""Strategy-agnostic, cash-only position sizing for existing BUY setups."""

from decimal import Decimal, ROUND_DOWN

from .models import PositionSizingRequest, PositionSizingResult


def _decimal(value: float) -> Decimal:
    """Convert via text so price arithmetic is not affected by binary floats."""
    return Decimal(str(value))


def _number(value: Decimal) -> float:
    """Keep the public API consistent with the project's numeric JSON models."""
    return float(value)


def calculate_position_size(request: PositionSizingRequest) -> PositionSizingResult:
    """Return the largest whole-share BUY position allowed by both constraints."""
    capital = _decimal(request.capital)
    risk_percent = _decimal(request.risk_percent)
    entry = _decimal(request.entry_price)
    stop = _decimal(request.stop_loss)
    target = _decimal(request.target_price)

    risk_capital = capital * risk_percent / Decimal("100")
    risk_per_share = entry - stop
    reward_per_share = target - entry

    risk_constraint_quantity = int((risk_capital / risk_per_share).to_integral_value(rounding=ROUND_DOWN))
    capital_constraint_quantity = int((capital / entry).to_integral_value(rounding=ROUND_DOWN))
    quantity = min(risk_constraint_quantity, capital_constraint_quantity)

    capital_required = Decimal(quantity) * entry
    actual_risk = Decimal(quantity) * risk_per_share
    expected_reward = Decimal(quantity) * reward_per_share
    risk_reward_ratio = reward_per_share / risk_per_share
    can_open = quantity > 0

    return PositionSizingResult(
        capital=_number(capital),
        risk_percent=_number(risk_percent),
        risk_capital=_number(risk_capital),
        entry_price=_number(entry),
        stop_loss=_number(stop),
        target_price=_number(target),
        risk_per_share=_number(risk_per_share),
        risk_constraint_quantity=risk_constraint_quantity,
        capital_constraint_quantity=capital_constraint_quantity,
        quantity=quantity,
        capital_required=_number(capital_required),
        actual_risk=_number(actual_risk),
        reward_per_share=_number(reward_per_share),
        expected_reward=_number(expected_reward),
        risk_reward_ratio=_number(risk_reward_ratio),
        constraints_satisfied=can_open,
        message=None if can_open else "Position cannot be opened within the specified risk/capital constraints.",
    )
