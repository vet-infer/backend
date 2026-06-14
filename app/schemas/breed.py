from pydantic import BaseModel, Field

from app.schemas.species import SpeciesOut


class BreedBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    species_id: int


class BreedCreate(BreedBase):
    pass


class BreedUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    species_id: int | None = None


class BreedOut(BreedBase):
    id: int
    species: SpeciesOut | None = None

    model_config = {"from_attributes": True}
