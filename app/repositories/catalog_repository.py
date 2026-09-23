from app.core.cache import cache
from app.models.clinical_variable import ClinicalVariable
from app.models.disease import Disease
from app.models.knowledge import FactDefinition
from app.models.symptom import Symptom
from app.repositories.base import BaseRepository
from app.repositories.snapshots import DiseaseSnapshot


class CatalogRepository(BaseRepository[Disease]):
    model = Disease

    def list_diseases(self, species_id: int | None = None) -> list[DiseaseSnapshot]:
        def _load() -> list[DiseaseSnapshot]:
            query = self.db.query(Disease).filter(Disease.is_active.is_(True))
            if species_id is not None:
                query = query.filter(Disease.species_id == species_id)
            diseases = query.order_by(Disease.species_id, Disease.name).all()
            return [DiseaseSnapshot.from_orm_disease(disease) for disease in diseases]

        return cache.get_or_set(f"diseases:{species_id}", _load)

    def create_disease(self, disease: Disease) -> Disease:
        return self.add(disease)

    def list_symptoms(self) -> list[Symptom]:
        return self.db.query(Symptom).filter(Symptom.is_active.is_(True)).all()

    def list_symptoms_admin(self) -> list[Symptom]:
        return self.db.query(Symptom).order_by(Symptom.species_id, Symptom.name).all()

    def get_symptom(self, symptom_id: int) -> Symptom | None:
        return self.db.get(Symptom, symptom_id)

    def set_symptom_fact_definitions_active(self, symptom_id: int, is_active: bool) -> None:
        self.db.query(FactDefinition).filter(FactDefinition.symptom_id == symptom_id).update(
            {"is_active": is_active}
        )

    def list_clinical_variables(self) -> list[ClinicalVariable]:
        return self.db.query(ClinicalVariable).filter(ClinicalVariable.is_active.is_(True)).all()
