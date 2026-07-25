from typing import Any

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, TimestampMixin


class InferenceResult(IDMixin, TimestampMixin, Base):
    __tablename__ = "inference_results"

    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id"), index=True)
    disease_id: Mapped[int] = mapped_column(ForeignKey("diseases.id"), index=True)
    risk_level_id: Mapped[int] = mapped_column(ForeignKey("risk_levels.id"), index=True)
    suggested_diagnosis: Mapped[str] = mapped_column(String(255))
    score: Mapped[float] = mapped_column(Float)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    inference_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    @property
    def risk_level(self) -> str:
        return self.risk_level_ref.name


class ActivatedRule(IDMixin, TimestampMixin, Base):
    __tablename__ = "activated_rules"

    result_id: Mapped[int] = mapped_column(ForeignKey("inference_results.id"), index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("inference_rules.id"), index=True)
    fulfilled_conditions: Mapped[Any] = mapped_column(JSON)
    justification: Mapped[str] = mapped_column(Text)
    rule_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rule_version: Mapped[int | None] = mapped_column(nullable=True)

    result = relationship("InferenceResult", back_populates="activated_rules")
    rule = relationship("InferenceRule", back_populates="activated_records")
