from typing import Any

from pydantic import BaseModel, Field


class RuleConditionCreate(BaseModel):
    variable_key: str = Field(min_length=1, max_length=100)
    operator: str = Field(min_length=1, max_length=30)
    expected_value: Any
    logical_group: int = Field(default=1, ge=1)


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
