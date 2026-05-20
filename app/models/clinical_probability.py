from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ClinicalProbability(Base):
    __tablename__ = "clinical_probabilities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    disease_id: Mapped[int] = mapped_column(ForeignKey("diseases.id", ondelete="CASCADE"), nullable=False)
    symptom_id: Mapped[int | None] = mapped_column(ForeignKey("symptoms.id", ondelete="CASCADE"), nullable=True)
    variable_id: Mapped[int | None] = mapped_column(ForeignKey("clinical_variables.id", ondelete="CASCADE"), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    probability_given_disease: Mapped[float] = mapped_column(Float, nullable=False)
    general_probability: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    disease = relationship("Disease")
    symptom = relationship("Symptom")
    variable = relationship("ClinicalVariable")
