from typing import Any

from pydantic import BaseModel, Field


class ClinicalFact(BaseModel):
    key: str
    value: Any


class InferenceRequest(BaseModel):
    patient_id: int
    evaluation_id: int | None = None
    facts: list[ClinicalFact] = Field(min_length=1)


class ActivatedRuleOut(BaseModel):
    rule_id: int
    rule_code: str
    rule_name: str
    fulfilled_conditions: list[str]
    justification: str


class InferenceResultOut(BaseModel):
    disease_id: int
    disease: str
    suggested_diagnosis: str
    risk_level: str
    score: float
    explanation: str
    activated_rules: list[ActivatedRuleOut]


class PersistedActivatedRuleOut(BaseModel):
    id: int
    rule_id: int
    fulfilled_conditions: Any
    justification: str

    model_config = {"from_attributes": True}


class PersistedInferenceResultOut(BaseModel):
    id: int
    evaluation_id: int
    disease_id: int
    suggested_diagnosis: str
    risk_level: str
    score: float
    explanation: str | None = None
    activated_rules: list[PersistedActivatedRuleOut] = []

    model_config = {"from_attributes": True}


class ClinicalHistoryOut(BaseModel):
    id: int
    patient_id: int
    evaluation_id: int | None = None
    event_type: str
    summary: str

    model_config = {"from_attributes": True}
