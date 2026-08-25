from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.evaluation import ClinicalFactIn, ClinicalFactOut


class InferenceRequest(BaseModel):
    patient_id: int
    evaluation_id: int | None = None
    facts: list[ClinicalFactIn] = Field(min_length=1)


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
    probability: float | None = None
    inference_method: str | None = None
    explanation: str
    activated_rules: list[ActivatedRuleOut]


class PersistedActivatedRuleOut(BaseModel):
    id: int
    rule_id: int
    fulfilled_conditions: Any
    justification: str
    rule_code: str | None = None
    rule_version: int | None = None

    model_config = {"from_attributes": True}


class PersistedInferenceResultOut(BaseModel):
    id: int
    evaluation_id: int
    patient_id: int
    disease_id: int
    risk_level_id: int
    suggested_diagnosis: str
    risk_level: str
    score: float
    probability: float | None = None
    inference_method: str | None = None
    explanation: str | None = None
    activated_rules: list[PersistedActivatedRuleOut] = []

    model_config = {"from_attributes": True}


class SpanishInferenceResult(BaseModel):
    enfermedad: str
    probabilidad: float | None = None
    nivel_riesgo: str
    resultado_sugerido: str
    reglas_activadas: list[str]
    explicacion: str | None = None


class SpanishInferenceResponse(BaseModel):
    evaluacion_id: int
    metodo_inferencia: str | None = None
    resultados: list[SpanishInferenceResult]


class ClinicalHistoryOut(BaseModel):
    id: int
    patient_id: int
    evaluation_id: int | None = None
    event_type: str
    summary: str
    created_at: datetime | None = None
    clinical_facts: list[ClinicalFactOut] = []

    model_config = {"from_attributes": True}
