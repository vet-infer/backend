import math
from typing import Any

from app.core.exceptions import AppException, NotFoundError
from app.models.clinical_history import ClinicalHistory
from app.models.knowledge import FactDefinition
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.evaluation import EvaluationCreate


class EvaluationService:
    def __init__(
        self,
        evaluation_repository: EvaluationRepository,
        patient_repository: PatientRepository,
    ):
        self.evaluation_repository = evaluation_repository
        self.patient_repository = patient_repository

    def create_evaluation(self, payload: EvaluationCreate, veterinarian_id: int):
        patient = self.patient_repository.get(payload.patient_id)
        if patient is None:
            raise NotFoundError("Paciente no encontrado")

        facts = self._validate_and_normalize_facts(payload.facts, patient.species_id)
        evaluation = self.evaluation_repository.create_with_facts(
            patient_id=payload.patient_id,
            veterinarian_id=veterinarian_id,
            reason=payload.reason,
            observations=payload.observations,
            facts=facts,
        )
        self.evaluation_repository.db.add(
            ClinicalHistory(
                patient_id=payload.patient_id,
                evaluation_id=evaluation.id,
                event_type="clinical_evaluation",
                summary="Se registro una evaluacion clinica veterinaria.",
            )
        )
        self.evaluation_repository.db.commit()
        self.evaluation_repository.db.refresh(evaluation)
        return evaluation

    def get_evaluation(self, evaluation_id: int):
        evaluation = self.evaluation_repository.get_with_facts(evaluation_id)
        if evaluation is None:
            raise NotFoundError("Evaluacion no encontrada")
        return evaluation

    def list_recent(self):
        return self.evaluation_repository.list_recent()

    def list_by_patient(self, patient_id: int):
        if self.patient_repository.get(patient_id) is None:
            raise NotFoundError("Paciente no encontrado")
        return self.evaluation_repository.list_by_patient(patient_id)

    def list_fact_definitions(self, species_id: int | None = None):
        return self._fact_definition_query(species_id).order_by(FactDefinition.source_type, FactDefinition.display_name).all()

    def list_fact_definitions_by_source(self, source_type: str, species_id: int | None = None):
        return (
            self._fact_definition_query(species_id)
            .filter(FactDefinition.source_type == source_type)
            .order_by(FactDefinition.display_name)
            .all()
        )

    def _fact_definition_query(self, species_id: int | None = None):
        query = self.evaluation_repository.db.query(FactDefinition).filter(FactDefinition.is_active.is_(True))
        if species_id is not None:
            query = query.filter(
                (FactDefinition.species_id == species_id) | (FactDefinition.species_id.is_(None))
            )
        return query

    def _validate_and_normalize_facts(self, facts, species_id: int) -> list[dict]:
        seen: set[str] = set()
        for submitted in facts:
            if submitted.fact_key in seen:
                raise AppException(f"El fact '{submitted.fact_key}' fue enviado mas de una vez")
            seen.add(submitted.fact_key)

        definitions: dict[str, FactDefinition] = {}
        rows = (
            self.evaluation_repository.db.query(FactDefinition)
            .filter(
                FactDefinition.fact_key.in_(seen),
                FactDefinition.is_active.is_(True),
                (FactDefinition.species_id == species_id) | (FactDefinition.species_id.is_(None)),
            )
            .order_by(FactDefinition.species_id.is_(None))
            .all()
        )
        for row in rows:
            definitions.setdefault(row.fact_key, row)

        normalized: list[dict] = []
        for submitted in facts:
            definition = definitions.get(submitted.fact_key)
            if definition is None:
                raise AppException(
                    f"Fact inexistente, inactivo o incompatible con la especie del paciente: {submitted.fact_key}"
                )
            if submitted.source_type not in {"clinical_input", definition.source_type}:
                raise AppException(
                    f"El fact '{submitted.fact_key}' pertenece a '{definition.source_type}' y no a '{submitted.source_type}'"
                )
            self._validate_fact_value(definition, submitted.value)
            normalized.append(
                {
                    "fact_key": submitted.fact_key,
                    "value": submitted.value,
                    "source_type": definition.source_type,
                }
            )
        return normalized

    @staticmethod
    def _validate_fact_value(definition: FactDefinition, value: Any) -> None:
        kind = definition.data_type.strip().lower()
        if kind in {"boolean", "bool"} and type(value) is not bool:
            raise AppException(f"El fact '{definition.fact_key}' debe ser booleano")
        if kind in {"numeric", "number", "float", "integer", "decimal"}:
            if type(value) is bool or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise AppException(f"El fact '{definition.fact_key}' debe ser numerico y finito")
        if kind in {"string", "text", "categorical", "select"} and not isinstance(value, str):
            raise AppException(f"El fact '{definition.fact_key}' debe ser categorico o textual")
        if definition.allowed_values is not None and value not in definition.allowed_values:
            raise AppException(
                f"Valor no permitido para '{definition.fact_key}'. Valores permitidos: {definition.allowed_values}"
            )
