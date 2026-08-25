from sqlalchemy import Boolean, ForeignKey, String, Text, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin


class Disease(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "diseases"
    __table_args__ = (UniqueConstraint("species_id", "name", name="uix_species_disease_name"),)

    name: Mapped[str] = mapped_column(String(120), index=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_probability: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.20)
    is_degenerative: Mapped[bool] = mapped_column(Boolean, default=True)

    species = relationship("Species", back_populates="diseases")
    rules = relationship("InferenceRule", back_populates="disease")
    results = relationship("InferenceResult", back_populates="disease")
