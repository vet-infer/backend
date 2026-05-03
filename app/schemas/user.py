from pydantic import BaseModel, EmailStr, Field


class RoleOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role_id: int


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    is_active: bool
    role: RoleOut | None = None

    model_config = {"from_attributes": True}
