from app.models.clinical_history import ClinicalHistory


class HistoryRepository:
    def __init__(self, db):
        self.db = db

    def list_by_patient(self, patient_id: int) -> list[ClinicalHistory]:
        return (
            self.db.query(ClinicalHistory)
            .filter(ClinicalHistory.patient_id == patient_id)
            .order_by(ClinicalHistory.created_at.desc())
            .all()
        )
