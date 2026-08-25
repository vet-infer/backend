"""add_missing_unique_constraints

Revision ID: c70422c97f1f
Revises: 7c1f146683e0
Create Date: 2026-08-01 16:12:56.896669
"""
from alembic import op
import sqlalchemy as sa


revision = 'c70422c97f1f'
down_revision = '7c1f146683e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint('uix_species_clinical_variable_key', 'clinical_variables', ['species_id', 'key'])
    op.create_unique_constraint('uix_species_disease_name', 'diseases', ['species_id', 'name'])
    op.create_unique_constraint('uix_species_symptom_name', 'symptoms', ['species_id', 'name'])


def downgrade() -> None:
    op.drop_constraint('uix_species_symptom_name', 'symptoms', type_='unique')
    op.drop_constraint('uix_species_disease_name', 'diseases', type_='unique')
    op.drop_constraint('uix_species_clinical_variable_key', 'clinical_variables', type_='unique')
