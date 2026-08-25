from typing import Any

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, TimestampMixin


class EvaluationClinical(IDMixin, TimestampMixin, Base):
    __tablename__ = "evaluations"

    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    veterinarian_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient = relationship("Patient", back_populates="evaluations")
    veterinarian = relationship("User", back_populates="evaluations")
    facts = relationship(
        "EvaluationClinicalFact",
        back_populates="evaluation",
        cascade="all, delete-orphan",
    )
    results = relationship("InferenceResult", back_populates="evaluation")
    history_events = relationship("ClinicalHistory", back_populates="evaluation")


class EvaluationClinicalFact(IDMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_facts"

    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    fact_key: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[Any] = mapped_column(JSON)
    source_type: Mapped[str] = mapped_column(String(40), default="clinical_input")

    evaluation = relationship("EvaluationClinical", back_populates="facts")
    patient = relationship("Patient")
