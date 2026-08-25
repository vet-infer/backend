from app.models.clinical_variable import ClinicalVariable
from app.models.disease import Disease
from app.models.symptom import Symptom
from app.repositories.base import BaseRepository


class CatalogRepository(BaseRepository[Disease]):
    model = Disease

    def list_diseases(self) -> list[Disease]:
        return self.db.query(Disease).filter(Disease.is_active.is_(True)).order_by(Disease.species_id, Disease.name).all()

    def create_disease(self, disease: Disease) -> Disease:
        return self.add(disease)

    def list_symptoms(self) -> list[Symptom]:
        return self.db.query(Symptom).filter(Symptom.is_active.is_(True)).all()

    def list_clinical_variables(self) -> list[ClinicalVariable]:
        return self.db.query(ClinicalVariable).filter(ClinicalVariable.is_active.is_(True)).all()
