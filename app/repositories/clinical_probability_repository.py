from app.models.clinical_probability import ClinicalProbability
from app.repositories.base import BaseRepository


class ClinicalProbabilityRepository(BaseRepository[ClinicalProbability]):
    model = ClinicalProbability

    # Spanish aliases and methods requested:
    def crear_probabilidad(self, prob_data: dict) -> ClinicalProbability:
        prob = ClinicalProbability(**prob_data)
        return self.add(prob)

    def obtener_probabilidad_por_id(self, entity_id: int) -> ClinicalProbability | None:
        return self.get(entity_id)

    def listar_probabilidades(self, skip: int = 0, limit: int = 100) -> list[ClinicalProbability]:
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
        return prob

    def desactivar_probabilidad(self, entity_id: int) -> ClinicalProbability | None:
        prob = self.get(entity_id)
        if not prob:
            return None
        prob.is_active = False
        self.db.commit()
        self.db.refresh(prob)
        return prob
