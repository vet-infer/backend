from app.core.cache import cache
from app.core.exceptions import NotFoundError
from app.models.disease import Disease
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.disease import CatalogStatusUpdate, DiseaseCreate


class CatalogService:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    def list_diseases(self):
        return self.repository.list_diseases()

    def create_disease(self, payload: DiseaseCreate):
        return self.repository.create_disease(Disease(**payload.model_dump()))

    def list_symptoms(self):
        return self.repository.list_symptoms()

    def list_symptoms_admin(self):
        return self.repository.list_symptoms_admin()

    def update_symptom_status(self, symptom_id: int, payload: CatalogStatusUpdate):
        symptom = self.repository.get_symptom(symptom_id)
        if symptom is None:
            raise NotFoundError("Sintoma no encontrado")
        symptom.is_active = payload.is_active
        self.repository.set_symptom_fact_definitions_active(symptom_id, payload.is_active)
        self.repository.db.commit()
        self.repository.db.refresh(symptom)
        cache.invalidate_all()
        return symptom

    def list_clinical_variables(self):
        return self.repository.list_clinical_variables()
