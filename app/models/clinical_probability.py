from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin


class ClinicalProbability(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "clinical_probabilities"

    disease_id: Mapped[int] = mapped_column(ForeignKey("diseases.id", ondelete="CASCADE"), nullable=False, index=True)
    symptom_id: Mapped[int | None] = mapped_column(ForeignKey("symptoms.id", ondelete="CASCADE"), nullable=True, index=True)
    variable_id: Mapped[int | None] = mapped_column(ForeignKey("clinical_variables.id", ondelete="CASCADE"), nullable=True, index=True)
    expected_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    probability_given_disease: Mapped[float] = mapped_column(Float, nullable=False)
    general_probability: Mapped[float] = mapped_column(Float, nullable=False)

    disease = relationship("Disease")
    symptom = relationship("Symptom")
    variable = relationship("ClinicalVariable")
