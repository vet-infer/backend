from app.models.disease import Disease
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.disease import DiseaseCreate


class CatalogService:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    def list_diseases(self):
        return self.repository.list_diseases()

    def create_disease(self, payload: DiseaseCreate):
        return self.repository.create_disease(Disease(**payload.model_dump()))

    def list_symptoms(self):
        return self.repository.list_symptoms()

    def list_clinical_variables(self):
        return self.repository.list_clinical_variables()
