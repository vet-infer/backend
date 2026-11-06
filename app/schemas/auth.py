from pydantic import BaseModel, Field

from app.core.security import RequiredPassword
from app.core.validation import RequiredEmail


class LoginRequest(BaseModel):
    email: RequiredEmail
    # Sin minimo de 8: una clave corta debe dar 401 "Credenciales invalidas", no 422.
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: RequiredPassword


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: RequiredEmail


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    new_password: RequiredPassword
