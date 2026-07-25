from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin


class Symptom(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "symptoms"

    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))

    species = relationship("Species", back_populates="symptoms")
