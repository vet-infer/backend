from pydantic import BaseModel, Field, field_validator

from app.core.validation import validate_email_format


class OwnerBase(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = None
    address: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value:
            return validate_email_format(value)
        return value


class OwnerCreate(OwnerBase):
    pass


class OwnerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=2, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = None
    address: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value:
            return validate_email_format(value)
        return value


class OwnerOut(OwnerBase):
    id: int

    model_config = {"from_attributes": True}
