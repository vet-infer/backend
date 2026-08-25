from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin


class ClinicalVariable(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "clinical_variables"
    __table_args__ = (UniqueConstraint("species_id", "key", name="uix_species_clinical_variable_key"),)

    key: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    data_type: Mapped[str] = mapped_column(String(30))
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    normal_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    normal_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    species_id: Mapped[int | None] = mapped_column(ForeignKey("species.id"), nullable=True)

    species = relationship("Species", back_populates="clinical_variables")
