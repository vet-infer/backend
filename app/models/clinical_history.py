from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, TimestampMixin


class ClinicalHistory(IDMixin, TimestampMixin, Base):
    __tablename__ = "clinical_history"

    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    evaluation_id: Mapped[int | None] = mapped_column(ForeignKey("evaluations.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(60))
    summary: Mapped[str] = mapped_column(Text)

    patient = relationship("Patient", back_populates="history_events")
    evaluation = relationship("EvaluationClinical", back_populates="history_events")
