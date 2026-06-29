from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EvaluationClinical(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    veterinarian_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="evaluations")
    veterinarian = relationship("User", back_populates="evaluations")
    facts = relationship(
        "EvaluationClinicalFact",
        back_populates="evaluation",
        cascade="all, delete-orphan",
    )
    results = relationship("InferenceResult", back_populates="evaluation")
    history_events = relationship("ClinicalHistory", back_populates="evaluation")


class EvaluationClinicalFact(Base):
    __tablename__ = "evaluation_facts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    fact_key: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[Any] = mapped_column(JSON)
    source_type: Mapped[str] = mapped_column(String(40), default="clinical_input")

    evaluation = relationship("EvaluationClinical", back_populates="facts")
    patient = relationship("Patient")
