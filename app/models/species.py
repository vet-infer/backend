from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True)

    patients = relationship("Patient", back_populates="species")
    breeds = relationship("Breed", back_populates="species", cascade="all, delete-orphan")
    diseases = relationship("Disease", back_populates="species")
    symptoms = relationship("Symptom", back_populates="species")
    clinical_variables = relationship("ClinicalVariable", back_populates="species")
