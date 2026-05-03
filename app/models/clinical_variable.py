from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ClinicalVariable(Base):
    __tablename__ = "clinical_variables"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    data_type: Mapped[str] = mapped_column(String(30))
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    normal_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    normal_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    species_id: Mapped[int | None] = mapped_column(ForeignKey("species.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    species = relationship("Species", back_populates="clinical_variables")
