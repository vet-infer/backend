from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True)

    patients = relationship("Patient", back_populates="species")
    diseases = relationship("Disease", back_populates="species")
    symptoms = relationship("Symptom", back_populates="species")
    clinical_variables = relationship("ClinicalVariable", back_populates="species")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id"))
    name: Mapped[str] = mapped_column(String(80), index=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    breed: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sex: Mapped[str] = mapped_column(String(20))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    species = relationship("Species", back_populates="patients")
    owner = relationship("Owner", back_populates="patients")
    creator = relationship("User", back_populates="patients_created")
    evaluations = relationship("EvaluationClinical", back_populates="patient")
    history_events = relationship("ClinicalHistory", back_populates="patient")
