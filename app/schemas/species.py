from pydantic import BaseModel, Field


class SpeciesBase(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class SpeciesCreate(SpeciesBase):
    pass


class SpeciesUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)


class SpeciesOut(SpeciesBase):
    id: int

    model_config = {"from_attributes": True}
