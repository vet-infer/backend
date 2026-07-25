from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.validation import OptionalEmail


class OwnerBase(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    email: OptionalEmail
    address: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=80)
    province: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    ubigeo: str | None = Field(default=None, pattern=r"^\d{6}$")

    @field_validator("department", "province", "district", "ubigeo", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class OwnerCreate(OwnerBase):
    pass


class OwnerUpdate(OwnerBase):
    first_name: str | None = Field(default=None, min_length=2, max_length=120)


class OwnerOut(OwnerBase):
    id: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
