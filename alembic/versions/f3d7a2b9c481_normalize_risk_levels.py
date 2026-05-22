"""normalize risk levels

Revision ID: f3d7a2b9c481
Revises: b2aeb44f214b
Create Date: 2026-05-21 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "f3d7a2b9c481"
down_revision = "b2aeb44f214b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("min_probability", sa.Float(), nullable=True),
        sa.Column("max_probability", sa.Float(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_levels_id"), "risk_levels", ["id"], unique=False)
    op.create_index(op.f("ix_risk_levels_code"), "risk_levels", ["code"], unique=True)

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO risk_levels
                (code, name, description, min_probability, max_probability, sort_order, is_active)
            VALUES
                ('bajo', 'Bajo', 'Riesgo clinico bajo o evidencia insuficiente para sospecha relevante.', 0.0, 0.3999, 1, true),
                ('moderado', 'Moderado', 'Riesgo clinico intermedio que requiere seguimiento o pruebas complementarias.', 0.40, 0.6999, 2, true),
                ('alto', 'Alto', 'Riesgo clinico alto compatible con alerta temprana prioritaria.', 0.70, 1.0, 3, true)
            """
        )
    )

    op.add_column("inference_rules", sa.Column("risk_level_id", sa.Integer(), nullable=True))
    op.add_column("inference_results", sa.Column("risk_level_id", sa.Integer(), nullable=True))

    connection.execute(
        sa.text(
            """
            UPDATE inference_rules ir
            SET risk_level_id = rl.id
            FROM risk_levels rl
            WHERE lower(ir.risk_level) = rl.code
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE inference_results res
            SET risk_level_id = rl.id
            FROM risk_levels rl
            WHERE lower(res.risk_level) = rl.code
            """
        )
    )

    moderate_id = connection.execute(
        sa.text("SELECT id FROM risk_levels WHERE code = 'moderado'")
    ).scalar_one()
    connection.execute(
        sa.text(
            "UPDATE inference_rules SET risk_level_id = :risk_level_id WHERE risk_level_id IS NULL"
        ),
        {"risk_level_id": moderate_id},
    )
    connection.execute(
        sa.text(
            "UPDATE inference_results SET risk_level_id = :risk_level_id WHERE risk_level_id IS NULL"
        ),
        {"risk_level_id": moderate_id},
    )

    op.alter_column("inference_rules", "risk_level_id", nullable=False)
    op.alter_column("inference_results", "risk_level_id", nullable=False)
    op.create_foreign_key(
        "fk_inference_rules_risk_level_id",
        "inference_rules",
        "risk_levels",
        ["risk_level_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_inference_results_risk_level_id",
        "inference_results",
        "risk_levels",
        ["risk_level_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_inference_results_risk_level_id",
        "inference_results",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_inference_rules_risk_level_id",
        "inference_rules",
        type_="foreignkey",
    )
    op.drop_column("inference_results", "risk_level_id")
    op.drop_column("inference_rules", "risk_level_id")
    op.drop_index(op.f("ix_risk_levels_code"), table_name="risk_levels")
    op.drop_index(op.f("ix_risk_levels_id"), table_name="risk_levels")
    op.drop_table("risk_levels")
