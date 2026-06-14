from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Breed(Base):
    __tablename__ = "breeds"
    __table_args__ = (
        UniqueConstraint("species_id", "name", name="uix_species_breed_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)

    species = relationship("Species", back_populates="breeds")
    patients = relationship("Patient", back_populates="breed")
