from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

disease_anatomical_regions = Table(
    "disease_anatomical_regions",
    Base.metadata,
    Column("disease_id", ForeignKey("diseases.id"), primary_key=True),
    Column("region_id", ForeignKey("anatomical_regions.id"), primary_key=True),
    Column("is_primary", Boolean, nullable=False, server_default="true"),
)


class AnatomicalRegion(Base):
    __tablename__ = "anatomical_regions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    mesh_name_dog: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mesh_name_cat: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    diseases = relationship(
        "Disease",
        secondary=disease_anatomical_regions,
        back_populates="regions",
    )


class DiseaseAnatomicalRegionLink(Base):
    """Read-only view of the disease<->region association row, exposing is_primary."""

    __table__ = disease_anatomical_regions

    region = relationship("AnatomicalRegion", viewonly=True)
