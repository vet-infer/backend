from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InferenceRule(Base):
    __tablename__ = "inference_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    disease_id: Mapped[int] = mapped_column(ForeignKey("diseases.id"))
    risk_level_id: Mapped[int] = mapped_column(ForeignKey("risk_levels.id"))
    risk_level: Mapped[str] = mapped_column(String(20), default="moderado")
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    disease = relationship("Disease", back_populates="rules")
    risk_level_ref = relationship("RiskLevel", back_populates="rules")
    conditions = relationship(
        "RuleCondition",
        back_populates="rule",
        cascade="all, delete-orphan",
    )
    activated_records = relationship("ActivatedRule", back_populates="rule")
    references = relationship("RuleReference", back_populates="rule", cascade="all, delete-orphan")


class RuleCondition(Base):
    __tablename__ = "rule_conditions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("inference_rules.id"))
    variable_key: Mapped[str] = mapped_column(String(100), index=True)
    operator: Mapped[str] = mapped_column(String(30))
    expected_value: Mapped[Any] = mapped_column(JSON)
    logical_group: Mapped[int] = mapped_column(Integer, default=1)

    rule = relationship("InferenceRule", back_populates="conditions")
