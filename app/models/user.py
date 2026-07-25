from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, SoftDeleteMixin, TimestampMixin


class User(IDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), index=True)

    role = relationship("Role", back_populates="users")
    patients_created = relationship("Patient", back_populates="creator")
    evaluations = relationship("EvaluationClinical", back_populates="veterinarian")
