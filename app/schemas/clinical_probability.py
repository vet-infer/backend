from pydantic import BaseModel, Field


class ClinicalProbabilityBase(BaseModel):
    disease_id: int
    symptom_id: int | None = None
    variable_id: int | None = None
    expected_value: str | None = None
    probability_given_disease: float = Field(..., ge=0.0, le=1.0)
    general_probability: float = Field(..., ge=0.0, le=1.0)
    is_active: bool = True


class ClinicalProbabilityCreate(ClinicalProbabilityBase):
    pass


class ClinicalProbabilityUpdate(BaseModel):
    disease_id: int | None = None
    symptom_id: int | None = None
    variable_id: int | None = None
    expected_value: str | None = None
    probability_given_disease: float | None = Field(None, ge=0.0, le=1.0)
    general_probability: float | None = Field(None, ge=0.0, le=1.0)
    is_active: bool | None = None


class ClinicalProbabilityOut(ClinicalProbabilityBase):
    id: int

    model_config = {"from_attributes": True}
