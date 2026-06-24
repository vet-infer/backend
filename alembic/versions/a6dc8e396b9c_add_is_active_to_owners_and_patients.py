"""add_is_active_to_owners_and_patients

Revision ID: a6dc8e396b9c
Revises: e9f3a7c5d812
Create Date: 2026-06-22 22:04:07.546732
"""
from alembic import op
import sqlalchemy as sa


revision = 'a6dc8e396b9c'
down_revision = 'e9f3a7c5d812'
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    
    owners_columns = {col["name"] for col in inspector.get_columns("owners")}
    if "is_active" not in owners_columns:
        op.add_column('owners', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
        
    patients_columns = {col["name"] for col in inspector.get_columns("patients")}
    if "is_active" not in patients_columns:
        op.add_column('patients', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    
    owners_columns = {col["name"] for col in inspector.get_columns("owners")}
    if "is_active" in owners_columns:
        op.drop_column('owners', 'is_active')
        
    patients_columns = {col["name"] for col in inspector.get_columns("patients")}
    if "is_active" in patients_columns:
        op.drop_column('patients', 'is_active')

