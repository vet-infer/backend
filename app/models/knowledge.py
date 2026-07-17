from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    citation: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    references = relationship("RuleReference", back_populates="source", cascade="all, delete-orphan")

class FactDefinition(Base):
    __tablename__ = "fact_definitions"
    __table_args__ = (UniqueConstraint("fact_key", "species_id", name="uq_fact_definition_key_species"),)
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fact_key: Mapped[str] = mapped_column(String(100), index=True)
    display_name: Mapped[str] = mapped_column(String(150))
    source_type: Mapped[str] = mapped_column(String(30))
    data_type: Mapped[str] = mapped_column(String(30))
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    allowed_values: Mapped[object | None] = mapped_column(JSON, nullable=True)
    species_id: Mapped[int | None] = mapped_column(ForeignKey("species.id"), nullable=True)
    symptom_id: Mapped[int | None] = mapped_column(ForeignKey("symptoms.id"), nullable=True)
    clinical_variable_id: Mapped[int | None] = mapped_column(ForeignKey("clinical_variables.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class RuleReference(Base):
    __tablename__ = "rule_references"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("inference_rules.id", ondelete="CASCADE"))
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"))
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule = relationship("InferenceRule", back_populates="references")
    source = relationship("KnowledgeSource", back_populates="references")
