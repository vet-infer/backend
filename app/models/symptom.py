from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Symptom(Base):
    __tablename__ = "symptoms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    species = relationship("Species", back_populates="symptoms")
