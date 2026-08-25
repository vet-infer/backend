from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin


class Patient(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "patients"

    owner_id: Mapped[int] = mapped_column(ForeignKey("owners.id"), index=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"), index=True)
    breed_id: Mapped[int | None] = mapped_column(ForeignKey("breeds.id"), nullable=True, index=True)
    sex: Mapped[str] = mapped_column(String(20))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    species = relationship("Species", back_populates="patients")
    breed = relationship("Breed", back_populates="patients")
    owner = relationship("Owner", back_populates="patients")
    creator = relationship("User", back_populates="patients_created")
    evaluations = relationship("EvaluationClinical", back_populates="patient")
    history_events = relationship("ClinicalHistory", back_populates="patient")
