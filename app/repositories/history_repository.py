from sqlalchemy.orm import joinedload

from app.models.clinical_history import ClinicalHistory
from app.models.evaluation import EvaluationClinical


class HistoryRepository:
    def __init__(self, db):
        self.db = db

    def list_by_patient(self, patient_id: int) -> list[ClinicalHistory]:
        events = (
            self.db.query(ClinicalHistory)
            .options(joinedload(ClinicalHistory.evaluation).joinedload(EvaluationClinical.facts))
            .filter(ClinicalHistory.patient_id == patient_id)
            .order_by(ClinicalHistory.created_at.desc())
            .all()
        )

        for event in events:
            event.clinical_facts = [
                fact
                for fact in (event.evaluation.facts if event.evaluation else [])
                if fact.patient_id == patient_id
            ]
        return events
