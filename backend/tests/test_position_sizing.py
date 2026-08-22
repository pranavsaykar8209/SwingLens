import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.main import app
from backend.risk import PositionSizingRequest, calculate_position_size


def setup(**overrides):
    values = dict(capital=100000, risk_percent=1, entry_price=500, stop_loss=480, target_price=560)
    values.update(overrides)
    return PositionSizingRequest(**values)


def test_basic_position_sizing_example():
    result = calculate_position_size(setup())
    assert result.risk_capital == 1000
    assert result.risk_per_share == 20
    assert result.risk_constraint_quantity == 50
    assert result.capital_constraint_quantity == 200
    assert result.quantity == 50
    assert result.capital_required == 25000
    assert result.actual_risk == 1000
    assert result.reward_per_share == 60
    assert result.expected_reward == 3000
    assert result.risk_reward_ratio == 3
    assert result.constraints_satisfied is True


def test_capital_constraint_limits_quantity():
    result = calculate_position_size(setup(capital=900, risk_percent=100, entry_price=500, stop_loss=400, target_price=700))
    assert result.risk_constraint_quantity == 9
    assert result.capital_constraint_quantity == 1
    assert result.quantity == 1


def test_risk_constraint_limits_quantity():
    result = calculate_position_size(setup(capital=100000, risk_percent=1, entry_price=500, stop_loss=400, target_price=700))
    assert result.risk_constraint_quantity == 10
    assert result.capital_constraint_quantity == 200
    assert result.quantity == 10


def test_zero_quantity_returns_clear_status():
    result = calculate_position_size(setup(capital=100, risk_percent=1, entry_price=500, stop_loss=480, target_price=560))
    assert result.quantity == 0
    assert result.constraints_satisfied is False
    assert result.message == "Position cannot be opened within the specified risk/capital constraints."


@pytest.mark.parametrize(
    "values",
    [
        {"capital": 0}, {"risk_percent": 0}, {"risk_percent": 101},
        {"entry_price": 0}, {"stop_loss": 0}, {"target_price": 0},
        {"stop_loss": 500}, {"stop_loss": 501}, {"target_price": 500}, {"target_price": 499},
    ],
)
def test_invalid_inputs_are_rejected(values):
    with pytest.raises(ValidationError):
        setup(**values)


def test_decimal_values_floor_quantity_without_rounding_up():
    result = calculate_position_size(setup(capital=1000, risk_percent=1, entry_price=123.45, stop_loss=120.12, target_price=130.11))
    assert result.risk_per_share == pytest.approx(3.33)
    assert result.risk_constraint_quantity == 3
    assert result.quantity == 3
    assert result.actual_risk == pytest.approx(9.99)
    assert result.risk_reward_ratio == pytest.approx(2.0)


def test_calculation_is_deterministic():
    assert calculate_position_size(setup()).model_dump() == calculate_position_size(setup()).model_dump()


def test_position_size_api_returns_calculated_result():
    response = TestClient(app).post("/api/risk/position-size", json={
        "capital": 100000, "risk_percent": 1, "entry_price": 500, "stop_loss": 480, "target_price": 560,
    })
    assert response.status_code == 200
    assert response.json()["quantity"] == 50
    assert response.json()["risk_reward_ratio"] == 3.0


def test_position_size_api_rejects_invalid_buy_setup():
    response = TestClient(app).post("/api/risk/position-size", json={
        "capital": 100000, "risk_percent": 1, "entry_price": 500, "stop_loss": 500, "target_price": 560,
    })
    assert response.status_code == 422
