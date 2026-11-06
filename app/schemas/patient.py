from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.owner import OwnerOut
from app.schemas.species import SpeciesOut
from app.schemas.breed import BreedOut

PatientSex = Literal["Macho", "Hembra"]


def _reject_future_birth_date(value: date | None) -> date | None:
    if value is not None and value > date.today():
        raise ValueError("La fecha de nacimiento no puede ser futura")
    return value


class PatientCreate(BaseModel):
    owner_id: int
    name: str = Field(min_length=1, max_length=80)
    species_id: int
    breed_id: int | None = None
    sex: PatientSex
    birth_date: date | None = None
    weight: float | None = Field(default=None, gt=0)

    _check_birth_date = field_validator("birth_date")(_reject_future_birth_date)


class PatientUpdate(BaseModel):
    owner_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)
    species_id: int | None = None
    breed_id: int | None = None
    sex: PatientSex | None = None
    birth_date: date | None = None
    weight: float | None = Field(default=None, gt=0)

    _check_birth_date = field_validator("birth_date")(_reject_future_birth_date)


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

