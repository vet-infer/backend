from pydantic import BaseModel, Field

from app.core.security import RequiredPassword
from app.core.validation import RequiredEmail


class LoginRequest(BaseModel):
    email: RequiredEmail
    password: RequiredPassword


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: RequiredPassword
    new_password: RequiredPassword


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: RequiredEmail


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    new_password: RequiredPassword
