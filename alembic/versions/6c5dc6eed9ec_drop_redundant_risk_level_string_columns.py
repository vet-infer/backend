"""drop_redundant_risk_level_string_columns

Revision ID: 6c5dc6eed9ec
Revises: 752aa0cfbb2a
Create Date: 2026-07-25 16:53:43.807212
"""
from alembic import op
import sqlalchemy as sa


revision = '6c5dc6eed9ec'
down_revision = '752aa0cfbb2a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('inference_results', 'risk_level')
    op.drop_column('inference_rules', 'risk_level')


def downgrade() -> None:
    op.add_column('inference_rules', sa.Column('risk_level', sa.VARCHAR(length=20), nullable=True))
    op.add_column('inference_results', sa.Column('risk_level', sa.VARCHAR(length=20), nullable=True))

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE inference_rules ir SET risk_level = rl.code "
            "FROM risk_levels rl WHERE ir.risk_level_id = rl.id"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE inference_results res SET risk_level = rl.name "
            "FROM risk_levels rl WHERE res.risk_level_id = rl.id"
        )
    )

    op.alter_column('inference_rules', 'risk_level', nullable=False, server_default='moderado')
    op.alter_column('inference_results', 'risk_level', nullable=False)
