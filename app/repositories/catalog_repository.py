from app.core.cache import cache
from app.models.clinical_variable import ClinicalVariable
from app.models.disease import Disease
from app.models.symptom import Symptom
from app.repositories.snapshots import DiseaseSnapshot


class CatalogRepository:
    def __init__(self, db):
        self.db = db

    def list_diseases(self, species_id: int | None = None) -> list[DiseaseSnapshot]:
        def _load() -> list[DiseaseSnapshot]:
            query = self.db.query(Disease).filter(Disease.is_active.is_(True))
            if species_id is not None:
                query = query.filter(Disease.species_id == species_id)
            diseases = query.order_by(Disease.species_id, Disease.name).all()
            return [DiseaseSnapshot.from_orm_disease(disease) for disease in diseases]

        return cache.get_or_set(f"diseases:{species_id}", _load)

    def create_disease(self, disease: Disease) -> Disease:
        self.db.add(disease)
        self.db.commit()
        self.db.refresh(disease)
        return disease

    def list_symptoms(self) -> list[Symptom]:
        return self.db.query(Symptom).filter(Symptom.is_active.is_(True)).all()

    def list_clinical_variables(self) -> list[ClinicalVariable]:
        return self.db.query(ClinicalVariable).filter(ClinicalVariable.is_active.is_(True)).all()
