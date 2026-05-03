from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ClinicalFactIn(BaseModel):
    fact_key: str = Field(min_length=1, max_length=100)
    value: Any
    source_type: str = "clinical_input"


class ClinicalFactOut(BaseModel):
    id: int
    fact_key: str
    value: Any
    source_type: str

    model_config = {"from_attributes": True}


class EvaluationCreate(BaseModel):
    patient_id: int
    reason: str | None = None
    observations: str | None = None
    facts: list[ClinicalFactIn] = []


class EvaluationOut(BaseModel):
    id: int
    patient_id: int
    veterinarian_id: int
    reason: str | None = None
    observations: str | None = None
    created_at: datetime
    facts: list[ClinicalFactOut] = []

    model_config = {"from_attributes": True}
