"""add owner document type and number

Revision ID: a1c9e0f4b6d2
Revises: ff022638cffa
Create Date: 2026-09-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "a1c9e0f4b6d2"
down_revision = "ff022638cffa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("owners", sa.Column("document_type", sa.String(length=10), nullable=True))
    op.add_column("owners", sa.Column("document_number", sa.String(length=20), nullable=True))

    op.drop_index(op.f("ix_owners_email"), table_name="owners")
    op.create_index(op.f("ix_owners_email"), "owners", ["email"], unique=False)

    op.create_index(
        "ix_owners_document_type_document_number",
        "owners",
        ["document_type", "document_number"],
        unique=True,
        postgresql_where=sa.text("document_type IS NOT NULL AND document_number IS NOT NULL"),
        sqlite_where=sa.text("document_type IS NOT NULL AND document_number IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_owners_document_type_document_number", table_name="owners")

    op.drop_index(op.f("ix_owners_email"), table_name="owners")
    op.create_index(op.f("ix_owners_email"), "owners", ["email"], unique=True)

    op.drop_column("owners", "document_number")
    op.drop_column("owners", "document_type")
