from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin


class RiskLevel(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "risk_levels"

    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=1)

    rules = relationship("InferenceRule", back_populates="risk_level_ref")
    results = relationship("InferenceResult", back_populates="risk_level_ref")
