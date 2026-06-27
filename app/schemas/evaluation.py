from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ClinicalFactIn(BaseModel):
    fact_key: str = Field(min_length=1, max_length=100)
    value: Any
    source_type: str = "clinical_input"


class ClinicalFactOut(BaseModel):
    id: int
    patient_id: int
    evaluation_id: int
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


class FactDefinitionOut(BaseModel):
    """Metadata exposed to the clinical form; it never exposes rule internals."""

    id: int
    fact_key: str
    display_name: str
    source_type: str
    data_type: str
    unit: str | None = None
    allowed_values: list[object] | None = None
    species_id: int | None = None
    is_active: bool

    model_config = {"from_attributes": True}
