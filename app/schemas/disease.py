from pydantic import BaseModel, Field


class DiseaseCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    species_id: int
    description: str | None = None
    is_degenerative: bool = True
    is_active: bool = True


class DiseaseOut(BaseModel):
    id: int
    name: str
    species_id: int
    description: str | None = None
    is_degenerative: bool
    is_active: bool

    model_config = {"from_attributes": True}


class CatalogItemOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    species_id: int | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class ClinicalVariableOut(BaseModel):
    id: int
    key: str
    name: str
    data_type: str
    unit: str | None = None
    normal_min: float | None = None
    normal_max: float | None = None
    species_id: int | None = None
    is_active: bool

    model_config = {"from_attributes": True}
