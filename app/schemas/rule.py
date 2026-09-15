from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

SUPPORTED_OPERATORS = ("eq", "neq", "gt", "gte", "lt", "lte", "between", "contains", "in")


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


class RuleConditionCreate(BaseModel):
    variable_key: str = Field(min_length=1, max_length=100)
    operator: Literal["eq", "neq", "gt", "gte", "lt", "lte", "between", "contains", "in"]
    expected_value: Any
    logical_group: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def _validate_expected_value_shape(self) -> "RuleConditionCreate":
        operator = self.operator
        value = self.expected_value

        if operator in ("gt", "gte", "lt", "lte"):
            if not _is_number(value):
                raise ValueError(
                    f"El operador '{operator}' requiere un expected_value numerico"
                )
        elif operator == "between":
            low = high = None
            if isinstance(value, dict):
                low, high = value.get("min"), value.get("max")
            elif isinstance(value, (list, tuple)) and len(value) == 2:
                low, high = value[0], value[1]
            if low is None or high is None or not _is_number(low) or not _is_number(high):
                raise ValueError(
                    "El operador 'between' requiere [min, max] o {'min': x, 'max': y} numericos"
                )
            if float(low) > float(high):
                raise ValueError("El operador 'between' requiere min <= max")
        elif operator == "in":
            if not isinstance(value, (list, tuple, str)):
                raise ValueError("El operador 'in' requiere una lista o un string")

        return self


class RuleConditionOut(BaseModel):
    id: int
    variable_key: str
    operator: str
    expected_value: Any
    logical_group: int = 1

    model_config = {"from_attributes": True}


class RuleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=3, max_length=150)
    disease_id: int
    risk_level_id: int | None = None
    risk_level: str = "moderado"
    weight: float = Field(default=1.0, gt=0)
    priority: int = Field(default=1, ge=1)
    version: int = Field(default=1, ge=1)
    is_active: bool = True
    conditions: list[RuleConditionCreate] = Field(min_length=1)


class RuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=150)
    disease_id: int | None = None
    risk_level_id: int | None = None
    risk_level: str | None = None
    weight: float | None = Field(default=None, gt=0)
    priority: int | None = Field(default=None, ge=1)
    version: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    conditions: list[RuleConditionCreate] | None = Field(default=None, min_length=1)


class RuleStatusUpdate(BaseModel):
    is_active: bool


class RuleOut(BaseModel):
    id: int
    code: str
    name: str
    disease_id: int
    risk_level_id: int
    risk_level: str
    weight: float
    priority: int
    version: int
    is_active: bool
    conditions: list[RuleConditionOut]

    model_config = {"from_attributes": True}
