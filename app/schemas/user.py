from pydantic import BaseModel, Field, field_validator

from app.core.security import validate_bcrypt_password_length
from app.core.validation import validate_email_format


class RoleOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    role_id: int

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validate_email_format(value)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        validate_bcrypt_password_length(value)
        return value


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=72)
    role_id: int | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_email_format(value)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        validate_bcrypt_password_length(value)
        return value


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    is_active: bool
    role: RoleOut | None = None

    model_config = {"from_attributes": True}
