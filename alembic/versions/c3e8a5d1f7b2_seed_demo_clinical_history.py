"""seed demo clinical history (owners, patients, evaluations, results)

Revision ID: c3e8a5d1f7b2
Revises: b7d3f1e9a2c4
Create Date: 2026-09-22 00:00:00.000000

Inserta datos historicos de demostracion desde alembic/data/demo_clinical_history.json,
generado por scripts/generate_demo_history.py con el motor real de inferencia.

- Se omite en produccion salvo que SEED_DEMO_DATA=true.
- Es idempotente: no hace nada si los propietarios demo ya existen.
- Los catalogos (especies, razas, enfermedades, reglas, niveles de riesgo) se resuelven
  por nombre/codigo, no por id, para funcionar en cualquier base.
- El downgrade elimina los propietarios demo (email *.demo@example.com) y todo lo asociado.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from app.core.config import settings


revision = "c3e8a5d1f7b2"
down_revision = "b7d3f1e9a2c4"
branch_labels = None
depends_on = None

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "demo_clinical_history.json"
DEMO_EMAIL_PATTERN = "%.demo@example.com"

owners = sa.table(
    "owners",
    sa.column("id", sa.Integer), sa.column("first_name", sa.String), sa.column("last_name", sa.String),
    sa.column("phone", sa.String), sa.column("email", sa.String), sa.column("document_type", sa.String),
    sa.column("document_number", sa.String), sa.column("address", sa.String),
    sa.column("department", sa.String), sa.column("province", sa.String), sa.column("district", sa.String),
    sa.column("ubigeo", sa.String), sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
)
patients = sa.table(
    "patients",
    sa.column("id", sa.Integer), sa.column("owner_id", sa.Integer), sa.column("name", sa.String),
    sa.column("species_id", sa.Integer), sa.column("breed_id", sa.Integer), sa.column("sex", sa.String),
    sa.column("birth_date", sa.Date), sa.column("weight", sa.Float), sa.column("created_by", sa.Integer),
    sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
)
evaluations = sa.table(
    "evaluations",
    sa.column("id", sa.Integer), sa.column("patient_id", sa.Integer), sa.column("veterinarian_id", sa.Integer),
    sa.column("reason", sa.String), sa.column("observations", sa.Text),
    sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
)
evaluation_facts = sa.table(
    "evaluation_facts",
    sa.column("evaluation_id", sa.Integer), sa.column("patient_id", sa.Integer), sa.column("fact_key", sa.String),
    sa.column("value", sa.JSON), sa.column("source_type", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
)
inference_results = sa.table(
    "inference_results",
    sa.column("id", sa.Integer), sa.column("evaluation_id", sa.Integer), sa.column("disease_id", sa.Integer),
    sa.column("risk_level_id", sa.Integer), sa.column("suggested_diagnosis", sa.String),
    sa.column("score", sa.Float), sa.column("probability", sa.Float), sa.column("inference_method", sa.String),
    sa.column("explanation", sa.Text), sa.column("is_current", sa.Boolean),
    sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
)
activated_rules = sa.table(
    "activated_rules",
    sa.column("result_id", sa.Integer), sa.column("rule_id", sa.Integer), sa.column("fulfilled_conditions", sa.JSON),
    sa.column("justification", sa.Text), sa.column("rule_code", sa.String), sa.column("rule_version", sa.Integer),
    sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
)
clinical_history = sa.table(
    "clinical_history",
    sa.column("patient_id", sa.Integer), sa.column("evaluation_id", sa.Integer), sa.column("event_type", sa.String),
    sa.column("summary", sa.Text),
    sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
)


def _should_seed() -> bool:
    if os.getenv("SEED_DEMO_DATA", "").strip().lower() in {"1", "true", "yes"}:
        return True
    return settings.environment.lower() not in {"production", "prod"}


def _resolve_veterinarian_id(conn) -> int | None:
    return conn.execute(
        sa.text(
            """
            SELECT u.id FROM users u JOIN roles r ON r.id = u.role_id
            WHERE u.is_active
            ORDER BY (u.email = 'vet@example.com') DESC, (r.name = 'veterinario') DESC, u.id
            LIMIT 1
            """
        )
    ).scalar()


def _insert_returning_id(conn, table, values: dict) -> int:
    return conn.execute(table.insert().values(**values).returning(table.c.id)).scalar_one()


def upgrade() -> None:
    if not _should_seed():
        return

    conn = op.get_bind()
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    demo_emails = [owner["email"] for owner in data["owners"]]
    already_seeded = conn.execute(
        sa.select(sa.func.count()).select_from(owners).where(owners.c.email.in_(demo_emails))
    ).scalar()
    if already_seeded:
        return

    veterinarian_id = _resolve_veterinarian_id(conn)
    if veterinarian_id is None:
        return

    species_ids = dict(conn.execute(sa.text("SELECT name, id FROM species")).all())
    breed_ids = {
        (species_id, name): breed_id
        for breed_id, species_id, name in conn.execute(sa.text("SELECT id, species_id, name FROM breeds")).all()
    }
    disease_ids = {
        (species_id, name): disease_id
        for disease_id, species_id, name in conn.execute(
            sa.text("SELECT id, species_id, name FROM diseases WHERE is_active")
        ).all()
    }
    risk_level_ids = {}
    for risk_id, code, name in conn.execute(sa.text("SELECT id, code, name FROM risk_levels")).all():
        risk_level_ids[code.lower()] = risk_id
        risk_level_ids[name.lower()] = risk_id
    rule_ids = dict(conn.execute(sa.text("SELECT code, id FROM inference_rules")).all())

    owner_ids = {}
    for owner in data["owners"]:
        created_at = datetime.fromisoformat(owner["created_at"])
        owner_ids[owner["key"]] = _insert_returning_id(
            conn,
            owners,
            {
                "first_name": owner["first_name"], "last_name": owner["last_name"], "phone": owner["phone"],
                "email": owner["email"], "document_type": owner["document_type"],
                "document_number": owner["document_number"], "address": owner["address"],
                "department": "Lima", "province": "Lima", "district": owner["district"],
                "ubigeo": owner["ubigeo"], "is_active": True, "created_at": created_at, "updated_at": created_at,
            },
        )

    patient_ids, patient_species = {}, {}
    for patient in data["patients"]:
        species_id = species_ids.get(patient["species"])
        if species_id is None:
            continue
        created_at = datetime.fromisoformat(patient["created_at"])
        patient_species[patient["key"]] = species_id
        patient_ids[patient["key"]] = _insert_returning_id(
            conn,
            patients,
            {
                "owner_id": owner_ids[patient["owner"]], "name": patient["name"], "species_id": species_id,
                "breed_id": breed_ids.get((species_id, patient["breed"])), "sex": patient["sex"],
                "birth_date": datetime.fromisoformat(patient["birth_date"]).date(), "weight": patient["weight"],
                "created_by": veterinarian_id, "is_active": True, "created_at": created_at, "updated_at": created_at,
            },
        )

    for evaluation in data["evaluations"]:
        patient_id = patient_ids.get(evaluation["patient"])
        if patient_id is None:
            continue
        species_id = patient_species[evaluation["patient"]]
        created_at = datetime.fromisoformat(evaluation["created_at"])
        inferred_at = created_at + timedelta(seconds=40)

        evaluation_id = _insert_returning_id(
            conn,
            evaluations,
            {
                "patient_id": patient_id, "veterinarian_id": veterinarian_id, "reason": evaluation["reason"],
                "observations": evaluation["observations"], "created_at": created_at, "updated_at": created_at,
            },
        )
        conn.execute(
            evaluation_facts.insert(),
            [
                {**fact, "evaluation_id": evaluation_id, "patient_id": patient_id,
                 "created_at": created_at, "updated_at": created_at}
                for fact in evaluation["facts"]
            ],
        )
        conn.execute(
            clinical_history.insert().values(
                patient_id=patient_id, evaluation_id=evaluation_id, event_type="clinical_evaluation",
                summary="Se registro una evaluacion clinica veterinaria.",
                created_at=created_at, updated_at=created_at,
            )
        )

        persisted_results = 0
        for result in evaluation["results"]:
            disease_id = disease_ids.get((species_id, result["disease"]))
            risk_level_id = risk_level_ids.get(result["risk_level"].lower())
            if disease_id is None or risk_level_id is None:
                continue
            result_id = _insert_returning_id(
                conn,
                inference_results,
                {
                    "evaluation_id": evaluation_id, "disease_id": disease_id, "risk_level_id": risk_level_id,
                    "suggested_diagnosis": result["suggested_diagnosis"], "score": result["score"],
                    "probability": result["probability"], "inference_method": result["inference_method"],
                    "explanation": result["explanation"], "is_current": True,
                    "created_at": inferred_at, "updated_at": inferred_at,
                },
            )
            persisted_results += 1
            rules = [
                {
                    "result_id": result_id, "rule_id": rule_ids[rule["rule_code"]],
                    "fulfilled_conditions": rule["fulfilled_conditions"], "justification": rule["justification"],
                    "rule_code": rule["rule_code"], "rule_version": rule["rule_version"],
                    "created_at": inferred_at, "updated_at": inferred_at,
                }
                for rule in result["activated_rules"]
                if rule["rule_code"] in rule_ids
            ]
            if rules:
                conn.execute(activated_rules.insert(), rules)

        conn.execute(
            clinical_history.insert().values(
                patient_id=patient_id, evaluation_id=evaluation_id, event_type="inference_result",
                summary=f"Se generaron {persisted_results} resultado(s) sugeridos por el motor de inferencia.",
                created_at=inferred_at, updated_at=inferred_at,
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    params = {"pattern": DEMO_EMAIL_PATTERN}
    demo_patients = "SELECT p.id FROM patients p JOIN owners o ON o.id = p.owner_id WHERE o.email LIKE :pattern"
    demo_evaluations = f"SELECT id FROM evaluations WHERE patient_id IN ({demo_patients})"
    demo_results = f"SELECT id FROM inference_results WHERE evaluation_id IN ({demo_evaluations})"

    conn.execute(sa.text(f"DELETE FROM activated_rules WHERE result_id IN ({demo_results})"), params)
    conn.execute(sa.text(f"DELETE FROM inference_results WHERE evaluation_id IN ({demo_evaluations})"), params)
    conn.execute(sa.text(f"DELETE FROM clinical_history WHERE patient_id IN ({demo_patients})"), params)
    conn.execute(sa.text(f"DELETE FROM evaluation_facts WHERE patient_id IN ({demo_patients})"), params)
    conn.execute(sa.text(f"DELETE FROM evaluations WHERE patient_id IN ({demo_patients})"), params)
    conn.execute(sa.text(f"DELETE FROM patients WHERE id IN ({demo_patients})"), params)
    conn.execute(sa.text("DELETE FROM owners WHERE email LIKE :pattern"), params)
