"""add patient traceability to evaluation facts

Revision ID: 6f2a9c1d0e45
Revises: a6dc8e396b9c
"""
from alembic import op
import sqlalchemy as sa

revision = "6f2a9c1d0e45"
down_revision = "a6dc8e396b9c"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("evaluation_facts")}

    if "patient_id" not in columns:
        op.add_column("evaluation_facts", sa.Column("patient_id", sa.Integer(), nullable=True))
        op.execute(
            sa.text(
                """
                UPDATE evaluation_facts
                SET patient_id = (
                    SELECT evaluations.patient_id
                    FROM evaluations
                    WHERE evaluations.id = evaluation_facts.evaluation_id
                )
                WHERE patient_id IS NULL
                """
            )
        )
        op.alter_column("evaluation_facts", "patient_id", nullable=False)
        op.create_index("ix_evaluation_facts_patient_id", "evaluation_facts", ["patient_id"])
        op.create_foreign_key(
            "fk_evaluation_facts_patient_id",
            "evaluation_facts",
            "patients",
            ["patient_id"],
            ["id"],
        )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("evaluation_facts")}

    if "patient_id" in columns:
        op.drop_constraint("fk_evaluation_facts_patient_id", "evaluation_facts", type_="foreignkey")
        op.drop_index("ix_evaluation_facts_patient_id", table_name="evaluation_facts")
        op.drop_column("evaluation_facts", "patient_id")
