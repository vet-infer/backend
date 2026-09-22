"""merge heads

Revision ID: ff022638cffa
Revises: c1a9e5f0b736, c70422c97f1f
Create Date: 2026-09-15 22:16:58.399703
"""
from alembic import op
import sqlalchemy as sa


revision = 'ff022638cffa'
down_revision = ('c1a9e5f0b736', 'c70422c97f1f')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
