from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin


class Breed(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "breeds"
    __table_args__ = (
        UniqueConstraint("species_id", "name", name="uix_species_breed_name"),
    )

    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)

    species = relationship("Species", back_populates="breeds")
    patients = relationship("Patient", back_populates="breed")
