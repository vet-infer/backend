from sqlalchemy.orm import joinedload

from app.core.cache import cache
from app.models.clinical_probability import ClinicalProbability
from app.core.config import settings
from app.repositories.base import BaseRepository
from app.repositories.snapshots import ClinicalProbabilitySnapshot


class ClinicalProbabilityRepository(BaseRepository[ClinicalProbability]):
    model = ClinicalProbability

    def list_active_by_disease_ids(self, disease_ids: list[int]) -> list[ClinicalProbabilitySnapshot]:
        key = "clinical_probabilities:" + ",".join(str(i) for i in sorted(disease_ids))

        def _load() -> list[ClinicalProbabilitySnapshot]:
            probs = (
                self.db.query(ClinicalProbability)
                .options(joinedload(ClinicalProbability.symptom), joinedload(ClinicalProbability.variable))
                .filter(ClinicalProbability.is_active.is_(True))
                .filter(ClinicalProbability.disease_id.in_(disease_ids))
                .all()
            )
            return [ClinicalProbabilitySnapshot.from_orm_probability(prob) for prob in probs]

        return cache.get_or_set(key, _load)

    # Spanish aliases and methods requested:
    def crear_probabilidad(self, prob_data: dict) -> ClinicalProbability:
        prob = ClinicalProbability(**prob_data)
        created = self.add(prob)
        cache.invalidate_all()
        return created

    def obtener_probabilidad_por_id(self, entity_id: int) -> ClinicalProbability | None:
        return self.get(entity_id)

    def listar_probabilidades(self, skip: int = 0, limit: int = settings.default_page_size) -> list[ClinicalProbability]:
        return self.db.query(ClinicalProbability).offset(skip).limit(limit).all()

    def listar_probabilidades_por_enfermedad(self, disease_id: int) -> list[ClinicalProbability]:
        return (
            self.db.query(ClinicalProbability)
            .filter(ClinicalProbability.disease_id == disease_id, ClinicalProbability.is_active == True)
            .all()
        )

    def buscar_probabilidad_por_evidencia(
        self, disease_id: int, symptom_id: int | None = None, variable_id: int | None = None
    ) -> ClinicalProbability | None:
        query = self.db.query(ClinicalProbability).filter(
            ClinicalProbability.disease_id == disease_id,
            ClinicalProbability.is_active == True
        )
        if symptom_id is not None:
            query = query.filter(ClinicalProbability.symptom_id == symptom_id)
        elif variable_id is not None:
            query = query.filter(ClinicalProbability.variable_id == variable_id)
        else:
            return None
        return query.first()

    def actualizar_probabilidad(self, entity_id: int, updates: dict) -> ClinicalProbability | None:
        prob = self.get(entity_id)
        if not prob:
            return None
        for key, val in updates.items():
            setattr(prob, key, val)
        self.db.commit()
        self.db.refresh(prob)
        cache.invalidate_all()
        return prob

    def desactivar_probabilidad(self, entity_id: int) -> ClinicalProbability | None:
        prob = self.get(entity_id)
        if not prob:
            return None
        prob.is_active = False
        self.db.commit()
        self.db.refresh(prob)
        cache.invalidate_all()
        return prob

