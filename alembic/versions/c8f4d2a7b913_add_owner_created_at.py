"""add owner created_at

Revision ID: c8f4d2a7b913
Revises: f3d7a2b9c481
Create Date: 2026-06-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "c8f4d2a7b913"
down_revision = "f3d7a2b9c481"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "owners",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("owners", "created_at")
