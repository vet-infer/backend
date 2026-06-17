from sqlalchemy.orm import joinedload

from app.models.evaluation import EvaluationClinical, EvaluationClinicalFact
from app.repositories.base import BaseRepository


class EvaluationRepository(BaseRepository[EvaluationClinical]):
    model = EvaluationClinical

    def get_with_facts(self, evaluation_id: int) -> EvaluationClinical | None:
        return (
            self.db.query(EvaluationClinical)
            .options(joinedload(EvaluationClinical.facts), joinedload(EvaluationClinical.patient))
            .filter(EvaluationClinical.id == evaluation_id)
            .first()
        )

    def list_by_patient(self, patient_id: int) -> list[EvaluationClinical]:
        return (
            self.db.query(EvaluationClinical)
            .options(joinedload(EvaluationClinical.facts))
            .filter(EvaluationClinical.patient_id == patient_id)
            .order_by(EvaluationClinical.created_at.desc())
            .all()
        )

    def list_recent(self, limit: int = 100) -> list[EvaluationClinical]:
        return (
            self.db.query(EvaluationClinical)
            .options(joinedload(EvaluationClinical.facts), joinedload(EvaluationClinical.patient))
            .order_by(EvaluationClinical.created_at.desc())
            .limit(limit)
            .all()
        )

    def create_with_facts(
        self,
        patient_id: int,
        veterinarian_id: int,
        reason: str | None,
        observations: str | None,
        facts: list[dict],
    ) -> EvaluationClinical:
        evaluation = EvaluationClinical(
            patient_id=patient_id,
            veterinarian_id=veterinarian_id,
            reason=reason,
            observations=observations,
        )
        evaluation.facts = [EvaluationClinicalFact(**fact) for fact in facts]
        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation
