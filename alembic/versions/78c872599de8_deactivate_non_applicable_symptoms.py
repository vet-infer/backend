"""deactivate non-applicable symptoms for gato and perro

Revision ID: 78c872599de8
Revises: c3e8a5d1f7b2
Create Date: 2026-09-23 00:00:00.000000

Desactiva un conjunto de sintomas de seed que no aplican para el flujo clinico
actual (solicitado explicitamente por el usuario), y propaga el mismo estado a
los fact_definitions enlazados (source_type="symptom"), que son los que
realmente alimentan el formulario de evaluaciones.

- Coincide por nombre (case-insensitive) + especie, no por id, para funcionar
  en cualquier base ya sembrada.
- Es idempotente: un UPDATE sobre filas ya inactivas no tiene efecto.
- El downgrade reactiva exactamente el mismo conjunto de sintomas/facts.
"""
from alembic import op
import sqlalchemy as sa


revision = "78c872599de8"
down_revision = "c3e8a5d1f7b2"
branch_labels = None
depends_on = None

# species_id: 1 = Perro, 2 = Gato
SYMPTOMS_TO_DEACTIVATE: list[tuple[int, str]] = [
    (2, "anemia"),
    (2, "acceso al exterior"),
    (2, "edad avanzada"),
    (2, "gingivoestomatitis cronica"),
    (2, "hiperactividad"),
    (2, "infecciones recurrentes"),
    (2, "lesiones orales ulcerativas o proliferativas"),
    (2, "movilidad dental"),
    (2, "recesion gingival"),
    (2, "sarro dental"),
    (1, "dificultad para masticar"),
    (1, "intolerancia al frio"),
    (1, "movilidad dental"),
    (1, "raza pequena"),
]


def _set_status(is_active: bool) -> None:
    connection = op.get_bind()
    for species_id, name in SYMPTOMS_TO_DEACTIVATE:
        symptom_id = connection.execute(
            sa.text(
                "SELECT id FROM symptoms WHERE species_id = :species_id AND lower(name) = lower(:name)"
            ),
            {"species_id": species_id, "name": name},
        ).scalar()
        if symptom_id is None:
            continue

        connection.execute(
            sa.text("UPDATE symptoms SET is_active = :is_active WHERE id = :id"),
            {"is_active": is_active, "id": symptom_id},
        )
        connection.execute(
            sa.text(
                "UPDATE fact_definitions SET is_active = :is_active WHERE symptom_id = :symptom_id"
            ),
            {"is_active": is_active, "symptom_id": symptom_id},
        )


def upgrade() -> None:
    _set_status(False)


def downgrade() -> None:
    _set_status(True)
