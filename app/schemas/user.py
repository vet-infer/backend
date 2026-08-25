from pydantic import BaseModel, Field

from app.core.security import OptionalPassword, RequiredPassword
from app.core.validation import OptionalEmail, RequiredEmail


class RoleOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: RequiredEmail
    password: RequiredPassword
    role_id: int


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    email: OptionalEmail
    password: OptionalPassword
    role_id: int | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    is_active: bool
    role: RoleOut | None = None

    model_config = {"from_attributes": True}
