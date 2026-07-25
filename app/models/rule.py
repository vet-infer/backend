from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin


class InferenceRule(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "inference_rules"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    disease_id: Mapped[int] = mapped_column(ForeignKey("diseases.id"), index=True)
    risk_level_id: Mapped[int] = mapped_column(ForeignKey("risk_levels.id"), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)

    disease = relationship("Disease", back_populates="rules")
    risk_level_ref = relationship("RiskLevel", back_populates="rules")
    conditions = relationship(
        "RuleCondition",
        back_populates="rule",
        cascade="all, delete-orphan",
    )
    activated_records = relationship("ActivatedRule", back_populates="rule")
    references = relationship("RuleReference", back_populates="rule", cascade="all, delete-orphan")

    @property
    def risk_level(self) -> str:
        return self.risk_level_ref.code


class RuleCondition(IDMixin, TimestampMixin, Base):
    __tablename__ = "rule_conditions"

    rule_id: Mapped[int] = mapped_column(ForeignKey("inference_rules.id"), index=True)
    variable_key: Mapped[str] = mapped_column(String(100), index=True)
    operator: Mapped[str] = mapped_column(String(30))
    expected_value: Mapped[Any] = mapped_column(JSON)
    logical_group: Mapped[int] = mapped_column(Integer, default=1)

    rule = relationship("InferenceRule", back_populates="conditions")
