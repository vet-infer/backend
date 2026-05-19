from pydantic import BaseModel, Field, field_validator

from app.core.security import validate_bcrypt_password_length
from app.core.validation import validate_email_format


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validate_email_format(value)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        validate_bcrypt_password_length(value)
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
