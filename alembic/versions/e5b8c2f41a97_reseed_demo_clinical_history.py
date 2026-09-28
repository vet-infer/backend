"""reseed demo clinical history

Revision ID: e5b8c2f41a97
Revises: 81bc1fcf6c62
Create Date: 2026-09-23 00:00:00.000000

Vuelve a ejecutar el seed de c3e8a5d1f7b2. En Railway esa revision quedo aplicada
antes de definir SEED_DEMO_DATA=true, por lo que no inserto datos y Alembic no la
repite. Reutiliza la misma logica: sigue condicionado a SEED_DEMO_DATA en produccion
y es idempotente (no hace nada si los propietarios demo ya existen).
"""
import importlib.util
from pathlib import Path


revision = "e5b8c2f41a97"
down_revision = "81bc1fcf6c62"
branch_labels = None
depends_on = None

SEED_MIGRATION = Path(__file__).resolve().parent / "c3e8a5d1f7b2_seed_demo_clinical_history.py"


def _load_seed_migration():
    spec = importlib.util.spec_from_file_location("seed_demo_clinical_history", SEED_MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upgrade() -> None:
    _load_seed_migration().upgrade()


def downgrade() -> None:
    # Los datos demo se eliminan con el downgrade de c3e8a5d1f7b2.
    pass
