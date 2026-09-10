"""add anatomical regions and disease mapping

Revision ID: d2b6f4a9c157
Revises: c1a9e5f0b736
Create Date: 2026-09-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "d2b6f4a9c157"
down_revision = "c1a9e5f0b736"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anatomical_regions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("mesh_name_dog", sa.String(length=80), nullable=True),
        sa.Column("mesh_name_cat", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_anatomical_regions_id"), "anatomical_regions", ["id"], unique=False)
    op.create_index(op.f("ix_anatomical_regions_code"), "anatomical_regions", ["code"], unique=True)

    op.create_table(
        "disease_anatomical_regions",
        sa.Column("disease_id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["disease_id"], ["diseases.id"]),
        sa.ForeignKeyConstraint(["region_id"], ["anatomical_regions.id"]),
        sa.PrimaryKeyConstraint("disease_id", "region_id"),
    )


def downgrade() -> None:
    op.drop_table("disease_anatomical_regions")
    op.drop_index(op.f("ix_anatomical_regions_code"), table_name="anatomical_regions")
    op.drop_index(op.f("ix_anatomical_regions_id"), table_name="anatomical_regions")
    op.drop_table("anatomical_regions")
