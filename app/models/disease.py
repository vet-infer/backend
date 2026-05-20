from sqlalchemy import Boolean, ForeignKey, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Disease(Base):
    __tablename__ = "diseases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_probability: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.20)
    is_degenerative: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    species = relationship("Species", back_populates="diseases")
    rules = relationship("InferenceRule", back_populates="disease")
    results = relationship("InferenceResult", back_populates="disease")
