from app.core.exceptions import NotFoundError
from app.models.clinical_history import ClinicalHistory
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

        facts = [fact.model_dump() for fact in payload.facts]
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
