from app.models.clinical_probability import ClinicalProbability
from app.core.config import settings
from app.repositories.base import BaseRepository


class ClinicalProbabilityRepository(BaseRepository[ClinicalProbability]):
    model = ClinicalProbability

    # Spanish aliases and methods requested:
    def crear_probabilidad(self, prob_data: dict) -> ClinicalProbability:
        prob = ClinicalProbability(**prob_data)
        return self.add(prob)

    def obtener_probabilidad_por_id(self, entity_id: int) -> ClinicalProbability | None:
        return self.get(entity_id)

    def listar_probabilidades(self, skip: int = 0, limit: int = settings.default_page_size) -> list[ClinicalProbability]:
        return (
            self.db.query(ClinicalProbability)
            .filter(ClinicalProbability.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def listar_por_enfermedades(self, disease_ids: list[int]) -> list[ClinicalProbability]:
        if not disease_ids:
            return []
        return (
            self.db.query(ClinicalProbability)
            .filter(
                ClinicalProbability.is_active == True,
                ClinicalProbability.disease_id.in_(disease_ids),
            )
            .all()
        )

    def listar_probabilidades_por_enfermedad(self, disease_id: int) -> list[ClinicalProbability]:
        return (
            self.db.query(ClinicalProbability)
            .filter(ClinicalProbability.disease_id == disease_id, ClinicalProbability.is_active == True)
            .all()
        )

    def actualizar_probabilidad(self, entity_id: int, updates: dict) -> ClinicalProbability | None:
        prob = self.get(entity_id)
        if not prob:
            return None
        return self.update(prob, updates)

    def desactivar_probabilidad(self, entity_id: int) -> ClinicalProbability | None:
        prob = self.get(entity_id)
        if not prob:
            return None
        self.delete(prob)
        return prob

