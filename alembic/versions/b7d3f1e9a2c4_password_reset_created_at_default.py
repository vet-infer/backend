"""add server default to password_reset_tokens.created_at

Revision ID: b7d3f1e9a2c4
Revises: a1c9e0f4b6d2
Create Date: 2026-09-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "b7d3f1e9a2c4"
down_revision = "a1c9e0f4b6d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("password_reset_tokens") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=sa.func.now(),
        )


def downgrade() -> None:
    with op.batch_alter_table("password_reset_tokens") as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=None,
        )
