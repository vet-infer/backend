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
    inspector = sa.inspect(op.get_bind())
    owners_columns = {c["name"] for c in inspector.get_columns("owners")}
    owners_indexes = {ix["name"]: ix for ix in inspector.get_indexes("owners")}

    if "document_type" not in owners_columns:
        op.add_column("owners", sa.Column("document_type", sa.String(length=10), nullable=True))
    if "document_number" not in owners_columns:
        op.add_column("owners", sa.Column("document_number", sa.String(length=20), nullable=True))

    email_index = owners_indexes.get(op.f("ix_owners_email"))
    if email_index is not None and email_index.get("unique"):
        op.drop_index(op.f("ix_owners_email"), table_name="owners")
        op.create_index(op.f("ix_owners_email"), "owners", ["email"], unique=False)
    elif email_index is None:
        op.create_index(op.f("ix_owners_email"), "owners", ["email"], unique=False)

    if "ix_owners_document_type_document_number" not in owners_indexes:
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
