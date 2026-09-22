from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin

_DOCUMENT_PRESENT = text("document_type IS NOT NULL AND document_number IS NOT NULL")


class Owner(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "owners"
    __table_args__ = (
        Index(
            "ix_owners_document_type_document_number",
            "document_type",
            "document_number",
            unique=True,
            postgresql_where=_DOCUMENT_PRESENT,
            sqlite_where=_DOCUMENT_PRESENT,
        ),
    )

    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    document_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(80), nullable=True)
    province: Mapped[str | None] = mapped_column(String(80), nullable=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ubigeo: Mapped[str | None] = mapped_column(String(6), nullable=True, index=True)

    patients = relationship("Patient", back_populates="owner")

