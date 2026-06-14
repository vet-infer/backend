from pydantic import BaseModel


class RiskLevelOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    min_probability: float | None = None
    max_probability: float | None = None
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}
