from app.models.clinical_history import ClinicalHistory
from app.models.evaluation import EvaluationClinicalFact
from app.repositories.base import BaseRepository


class HistoryRepository(BaseRepository[ClinicalHistory]):
    model = ClinicalHistory

    def list_by_patient(self, patient_id: int) -> list[ClinicalHistory]:
        events = (
            self.db.query(ClinicalHistory)
            .filter(ClinicalHistory.patient_id == patient_id)
            .order_by(ClinicalHistory.created_at.desc())
            .all()
        )

        evaluation_ids = [event.evaluation_id for event in events if event.evaluation_id is not None]
        facts_by_evaluation: dict[int, list[EvaluationClinicalFact]] = {}
        if evaluation_ids:
            facts = (
                self.db.query(EvaluationClinicalFact)
                .filter(
                    EvaluationClinicalFact.patient_id == patient_id,
                    EvaluationClinicalFact.evaluation_id.in_(evaluation_ids),
                )
                .all()
            )
            for fact in facts:
                facts_by_evaluation.setdefault(fact.evaluation_id, []).append(fact)

        for event in events:
            event.clinical_facts = facts_by_evaluation.get(event.evaluation_id, [])
        return events
