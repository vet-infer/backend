"""add is_current and superseded_at to inference_results

Revision ID: c1a9e5f0b736
Revises: 9b7c1d4e2a63
Create Date: 2026-09-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "c1a9e5f0b736"
down_revision = "9b7c1d4e2a63"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("inference_results")}

    if "is_current" not in columns:
        op.add_column(
            "inference_results",
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if "superseded_at" not in columns:
        op.add_column(
            "inference_results",
            sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns("inference_results")}

    if "superseded_at" in columns:
        op.drop_column("inference_results", "superseded_at")
    if "is_current" in columns:
        op.drop_column("inference_results", "is_current")
