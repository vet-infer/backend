"""add owner ubigeo fields

Revision ID: 9b7c1d4e2a63
Revises: 6f2a9c1d0e45
Create Date: 2026-06-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "9b7c1d4e2a63"
down_revision = "6f2a9c1d0e45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    owner_columns = {col["name"] for col in inspector.get_columns("owners")}

    if "department" not in owner_columns:
        op.add_column("owners", sa.Column("department", sa.String(length=80), nullable=True))
    if "province" not in owner_columns:
        op.add_column("owners", sa.Column("province", sa.String(length=80), nullable=True))
    if "district" not in owner_columns:
        op.add_column("owners", sa.Column("district", sa.String(length=80), nullable=True))
    if "ubigeo" not in owner_columns:
        op.add_column("owners", sa.Column("ubigeo", sa.String(length=6), nullable=True))
        op.create_index("ix_owners_ubigeo", "owners", ["ubigeo"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    owner_columns = {col["name"] for col in inspector.get_columns("owners")}
    indexes = {idx["name"] for idx in inspector.get_indexes("owners")}

    if "ix_owners_ubigeo" in indexes:
        op.drop_index("ix_owners_ubigeo", table_name="owners")
    if "ubigeo" in owner_columns:
        op.drop_column("owners", "ubigeo")
    if "district" in owner_columns:
        op.drop_column("owners", "district")
    if "province" in owner_columns:
        op.drop_column("owners", "province")
    if "department" in owner_columns:
        op.drop_column("owners", "department")