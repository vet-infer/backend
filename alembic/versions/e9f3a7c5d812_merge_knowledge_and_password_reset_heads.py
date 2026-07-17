"""merge knowledge-base and password-reset migration heads

Revision ID: e9f3a7c5d812
Revises: a6e4c1d2f901, d4e6f8a0b124
Create Date: 2026-06-21 00:00:00.000000

This merge revision has no schema operations.  It makes the two independent,
already-safe migration branches a single Alembic head so Railway can execute
``alembic upgrade head`` deterministically during pre-deploy.
"""

revision = "e9f3a7c5d812"
down_revision = ("a6e4c1d2f901", "d4e6f8a0b124")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
