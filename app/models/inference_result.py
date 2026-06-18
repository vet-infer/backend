from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InferenceResult(Base):
    __tablename__ = "inference_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id"))
    disease_id: Mapped[int] = mapped_column(ForeignKey("diseases.id"))
    risk_level_id: Mapped[int] = mapped_column(ForeignKey("risk_levels.id"))
    suggested_diagnosis: Mapped[str] = mapped_column(String(255))
    risk_level: Mapped[str] = mapped_column(String(20))
    score: Mapped[float] = mapped_column(Float)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    inference_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    evaluation = relationship("EvaluationClinical", back_populates="results")
    disease = relationship("Disease", back_populates="results")
    risk_level_ref = relationship("RiskLevel", back_populates="results")
    activated_rules = relationship(
        "ActivatedRule",
        back_populates="result",
        cascade="all, delete-orphan",
    )

    @property
    def patient_id(self) -> int:
        return self.evaluation.patient_id


class ActivatedRule(Base):
    __tablename__ = "activated_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("inference_results.id"))
    rule_id: Mapped[int] = mapped_column(ForeignKey("inference_rules.id"))
    fulfilled_conditions: Mapped[Any] = mapped_column(JSON)
    justification: Mapped[str] = mapped_column(Text)

    result = relationship("InferenceResult", back_populates="activated_rules")
    rule = relationship("InferenceRule", back_populates="activated_records")
