from app.repositories.history_repository import HistoryRepository


class HistoryService:
    def __init__(self, repository: HistoryRepository):
        self.repository = repository

    def list_by_patient(self, patient_id: int):
        return self.repository.list_by_patient(patient_id)
