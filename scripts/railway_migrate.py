from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import engine


BASELINE_BAYES = "b2aeb44f214b"
BASELINE_RISK_LEVELS = "f3d7a2b9c481"
HEAD = "head"


def has_column(inspector, table_name: str, column_name: str) -> bool:
    if table_name not in inspector.get_table_names():
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def alembic_has_version() -> bool:
    with engine.connect() as connection:
        if "alembic_version" not in inspect(connection).get_table_names():
            return False
        version = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        return bool(version)


def infer_existing_schema_revision() -> str | None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "owners" not in tables:
        return None

    bayes_schema_exists = {
        "owners",
        "breeds",
        "clinical_probabilities",
    }.issubset(tables) and all(
        [
            has_column(inspector, "patients", "owner_id"),
            has_column(inspector, "patients", "breed_id"),
            has_column(inspector, "diseases", "base_probability"),
            has_column(inspector, "inference_results", "probability"),
            has_column(inspector, "inference_results", "inference_method"),
        ]
    )
    if not bayes_schema_exists:
        raise RuntimeError(
            "Existing schema has owners table but is missing expected Bayes migration columns. "
            "Manual database review required before stamping Alembic."
        )

    risk_schema_exists = "risk_levels" in tables and all(
        [
            has_column(inspector, "inference_rules", "risk_level_id"),
            has_column(inspector, "inference_results", "risk_level_id"),
        ]
    )
    if not risk_schema_exists:
        return BASELINE_BAYES

    if not has_column(inspector, "owners", "created_at"):
        return BASELINE_RISK_LEVELS

    return HEAD


def main() -> None:
    config = Config("alembic.ini")

    if not alembic_has_version():
        inferred_revision = infer_existing_schema_revision()
        if inferred_revision is not None:
            print(f"Stamping existing Railway schema at {inferred_revision}.")
            command.stamp(config, inferred_revision)

    print("Running Alembic upgrade head.")
    command.upgrade(config, HEAD)


if __name__ == "__main__":
    main()
