"""Pydantic models for the standalone BUY position-sizing calculator."""

from pydantic import BaseModel, Field, model_validator


class PositionSizingRequest(BaseModel):
    """Inputs required to size a cash equity BUY position."""

    capital: float = Field(gt=0, description="Available account capital")
    risk_percent: float = Field(gt=0, le=100, description="Maximum account risk percentage")
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    target_price: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_buy_setup(self) -> "PositionSizingRequest":
        if self.stop_loss >= self.entry_price:
            raise ValueError("stop_loss must be below entry_price for a BUY setup")
        if self.target_price <= self.entry_price:
            raise ValueError("target_price must be above entry_price for a BUY setup")
        return self


class PositionSizingResult(BaseModel):
    """Deterministic result of applying risk and cash constraints to a BUY setup."""

    capital: float
    risk_percent: float
    risk_capital: float
    entry_price: float
    stop_loss: float
    target_price: float
    risk_per_share: float
    risk_constraint_quantity: int
    capital_constraint_quantity: int
    quantity: int
    capital_required: float
    actual_risk: float
    reward_per_share: float
    expected_reward: float
    risk_reward_ratio: float
    constraints_satisfied: bool
    message: str | None = None
