"""add knowledge base traceability

Revision ID: d4e6f8a0b124
Revises: c8f4d2a7b913
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e6f8a0b124"
down_revision = "c8f4d2a7b913"
branch_labels = None
depends_on = None

def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "knowledge_sources" not in tables:
        op.create_table("knowledge_sources", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(300), nullable=False), sa.Column("citation", sa.Text(), nullable=False), sa.Column("url", sa.String(500)), sa.Column("doi", sa.String(200)), sa.Column("publication_year", sa.Integer()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "fact_definitions" not in tables:
        op.create_table("fact_definitions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("fact_key", sa.String(100), nullable=False), sa.Column("display_name", sa.String(150), nullable=False), sa.Column("source_type", sa.String(30), nullable=False), sa.Column("data_type", sa.String(30), nullable=False), sa.Column("unit", sa.String(40)), sa.Column("allowed_values", sa.JSON()), sa.Column("species_id", sa.Integer(), sa.ForeignKey("species.id")), sa.Column("symptom_id", sa.Integer(), sa.ForeignKey("symptoms.id")), sa.Column("clinical_variable_id", sa.Integer(), sa.ForeignKey("clinical_variables.id")), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.UniqueConstraint("fact_key", "species_id", name="uq_fact_definition_key_species"))
    if "rule_references" not in tables:
        op.create_table("rule_references", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("rule_id", sa.Integer(), sa.ForeignKey("inference_rules.id", ondelete="CASCADE"), nullable=False), sa.Column("source_id", sa.Integer(), sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False), sa.Column("rationale", sa.Text()), sa.Column("locator", sa.String(100)))
    rule_columns = {column["name"] for column in inspector.get_columns("rule_conditions")}
    if "logical_group" not in rule_columns:
        op.add_column("rule_conditions", sa.Column("logical_group", sa.Integer(), nullable=False, server_default="1"))
    activated_columns = {column["name"] for column in inspector.get_columns("activated_rules")}
    if "rule_code" not in activated_columns:
        op.add_column("activated_rules", sa.Column("rule_code", sa.String(50)))
    if "rule_version" not in activated_columns:
        op.add_column("activated_rules", sa.Column("rule_version", sa.Integer()))

def downgrade():
    op.drop_column("activated_rules", "rule_version")
    op.drop_column("activated_rules", "rule_code")
    op.drop_column("rule_conditions", "logical_group")
    op.drop_table("rule_references")
    op.drop_table("fact_definitions")
    op.drop_table("knowledge_sources")
