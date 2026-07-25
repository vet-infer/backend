from app.core.exceptions import NotFoundError
from app.models.clinical_probability import ClinicalProbability
from app.repositories.clinical_probability_repository import ClinicalProbabilityRepository


class ClinicalProbabilityService:
    def __init__(self, repository: ClinicalProbabilityRepository):
        self.repository = repository

    def create_probability(self, data: dict) -> ClinicalProbability:
        return self.repository.crear_probabilidad(data)

    def list_probabilities(
        self, disease_id: int | None, skip: int = 0, limit: int = 50
    ) -> list[ClinicalProbability]:
        if disease_id is not None:
            return self.repository.listar_probabilidades_por_enfermedad(disease_id)
        return self.repository.listar_probabilidades(skip=skip, limit=limit)

    def get_probability(self, probability_id: int) -> ClinicalProbability:
        prob = self.repository.obtener_probabilidad_por_id(probability_id)
        if prob is None:
            raise NotFoundError("Probabilidad clinica no encontrada")
        return prob

    def update_probability(self, probability_id: int, updates: dict) -> ClinicalProbability:
        prob = self.repository.actualizar_probabilidad(probability_id, updates)
        if prob is None:
            raise NotFoundError("Probabilidad clinica no encontrada o no se pudo actualizar")
        return prob

    def delete_probability(self, probability_id: int) -> ClinicalProbability:
        prob = self.repository.desactivar_probabilidad(probability_id)
        if prob is None:
            raise NotFoundError("Probabilidad clinica no encontrada o no se pudo desactivar")
        return prob
