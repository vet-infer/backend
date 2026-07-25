"""baseline pre-bayes schema

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-07-25 00:00:00.000000

Reconstruye el esquema tal como existia antes de la migracion
``b2aeb44f214b`` (la primera migracion registrada en este repositorio,
la cual ya asumia columnas/tablas creadas fuera de Alembic via
``Base.metadata.create_all``). Sin esta migracion, ``alembic upgrade head``
falla contra una base de datos vacia porque ``b2aeb44f214b`` intenta
alterar tablas que ninguna migracion anterior crea.

Esta migracion no afecta bases de datos ya existentes: los ids de las
revisiones posteriores no cambian, por lo que un ``alembic_version``
ya estampado en una base real sigue siendo valido.
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    op.create_table(
        "species",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_species_id"), "species", ["id"], unique=False)
    op.create_index(op.f("ix_species_name"), "species", ["name"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "symptoms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("species_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["species_id"], ["species.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_symptoms_id"), "symptoms", ["id"], unique=False)
    op.create_index(op.f("ix_symptoms_name"), "symptoms", ["name"], unique=False)

    op.create_table(
        "clinical_variables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("data_type", sa.String(length=30), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("normal_min", sa.Float(), nullable=True),
        sa.Column("normal_max", sa.Float(), nullable=True),
        sa.Column("species_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["species_id"], ["species.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clinical_variables_id"), "clinical_variables", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_variables_key"), "clinical_variables", ["key"], unique=False)

    op.create_table(
        "diseases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("species_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_degenerative", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["species_id"], ["species.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diseases_id"), "diseases", ["id"], unique=False)
    op.create_index(op.f("ix_diseases_name"), "diseases", ["name"], unique=False)

    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tutor_name", sa.String(length=120), nullable=False),
        sa.Column("breed", sa.String(length=80), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("species_id", sa.Integer(), nullable=False),
        sa.Column("sex", sa.String(length=20), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["species_id"], ["species.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patients_id"), "patients", ["id"], unique=False)
    op.create_index(op.f("ix_patients_name"), "patients", ["name"], unique=False)

    op.create_table(
        "inference_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("disease_id", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="moderado"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["disease_id"], ["diseases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inference_rules_id"), "inference_rules", ["id"], unique=False)
    op.create_index(op.f("ix_inference_rules_code"), "inference_rules", ["code"], unique=True)

    op.create_table(
        "rule_conditions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("variable_key", sa.String(length=100), nullable=False),
        sa.Column("operator", sa.String(length=30), nullable=False),
        sa.Column("expected_value", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["inference_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rule_conditions_id"), "rule_conditions", ["id"], unique=False)
    op.create_index(op.f("ix_rule_conditions_variable_key"), "rule_conditions", ["variable_key"], unique=False)

    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("veterinarian_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["veterinarian_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evaluations_id"), "evaluations", ["id"], unique=False)

    op.create_table(
        "evaluation_facts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=False),
        sa.Column("fact_key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="clinical_input"),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evaluation_facts_id"), "evaluation_facts", ["id"], unique=False)
    op.create_index(op.f("ix_evaluation_facts_fact_key"), "evaluation_facts", ["fact_key"], unique=False)

    op.create_table(
        "inference_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=False),
        sa.Column("disease_id", sa.Integer(), nullable=False),
        sa.Column("suggested_diagnosis", sa.String(length=255), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"]),
        sa.ForeignKeyConstraint(["disease_id"], ["diseases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inference_results_id"), "inference_results", ["id"], unique=False)

    op.create_table(
        "activated_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("fulfilled_conditions", sa.JSON(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["result_id"], ["inference_results.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["inference_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activated_rules_id"), "activated_rules", ["id"], unique=False)

    op.create_table(
        "clinical_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clinical_history_id"), "clinical_history", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("clinical_history")
    op.drop_table("activated_rules")
    op.drop_table("inference_results")
    op.drop_table("evaluation_facts")
    op.drop_table("evaluations")
    op.drop_table("rule_conditions")
    op.drop_table("inference_rules")
    op.drop_table("patients")
    op.drop_table("diseases")
    op.drop_table("clinical_variables")
    op.drop_table("symptoms")
    op.drop_table("users")
    op.drop_table("species")
    op.drop_table("roles")
