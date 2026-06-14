from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.owner import OwnerOut
from app.schemas.species import SpeciesOut
from app.schemas.breed import BreedOut


class PatientCreate(BaseModel):
    owner_id: int
    name: str = Field(min_length=1, max_length=80)
    species_id: int
    breed_id: int | None = None
    sex: str
    birth_date: date | None = None
    weight: float | None = Field(default=None, gt=0)


class PatientUpdate(BaseModel):
    owner_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)
    species_id: int | None = None
    breed_id: int | None = None
    sex: str | None = None
    birth_date: date | None = None
    weight: float | None = Field(default=None, gt=0)


class PatientOut(BaseModel):
    id: int
    owner: OwnerOut
    name: str
    species: SpeciesOut
    breed: BreedOut | None = None
    sex: str
    birth_date: date | None = None
    weight: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

