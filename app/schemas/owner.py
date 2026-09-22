import re
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.validation import OptionalEmail

DNI_PATTERN = re.compile(r"^\d{8}$")
FOREIGN_DOCUMENT_PATTERN = re.compile(r"^[A-Za-z0-9]{1,12}$")


class DocumentType(str, Enum):
    DNI = "DNI"
    CE = "CE"
    PASSPORT = "PASSPORT"


class OwnerBase(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    email: OptionalEmail
    document_type: DocumentType | None = Field(default=None)
    document_number: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=80)
    province: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    ubigeo: str | None = Field(default=None, pattern=r"^\d{6}$")

    @field_validator("department", "province", "district", "ubigeo", "document_number", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @model_validator(mode="after")
    def validate_document(self) -> "OwnerBase":
        if self.document_type is None and self.document_number is None:
            return self
        if self.document_type is None or self.document_number is None:
            raise ValueError("Debe indicar tipo y numero de documento juntos")

        if self.document_type == DocumentType.DNI:
            if not DNI_PATTERN.fullmatch(self.document_number):
                raise ValueError("El DNI debe tener exactamente 8 digitos numericos")
        else:
            if not FOREIGN_DOCUMENT_PATTERN.fullmatch(self.document_number):
                raise ValueError("El numero de documento debe ser alfanumerico de hasta 12 caracteres")

        return self


class OwnerCreate(OwnerBase):
    pass


class OwnerUpdate(OwnerBase):
    first_name: str | None = Field(default=None, min_length=2, max_length=120)


class OwnerOut(OwnerBase):
    id: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
