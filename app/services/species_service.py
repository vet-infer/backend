from app.core.exceptions import ConflictError, NotFoundError
from app.models.species import Species
from app.repositories.species_repository import SpeciesRepository
from app.schemas.species import SpeciesCreate, SpeciesUpdate


class SpeciesService:
    def __init__(self, repository: SpeciesRepository):
        self.repository = repository

    def list_species(self, skip: int = 0, limit: int = 100) -> list[Species]:
        return self.repository.list(skip=skip, limit=limit)

    def get_species(self, species_id: int) -> Species:
        species = self.repository.get(species_id)
        if species is None:
            raise NotFoundError("Especie no encontrada")
        return species

    def create_species(self, payload: SpeciesCreate) -> Species:
        if self.repository.get_by_name(payload.name):
            raise ConflictError("Ya existe una especie con ese nombre")
        species = Species(**payload.model_dump())
        return self.repository.add(species)

    def update_species(self, species_id: int, payload: SpeciesUpdate) -> Species:
        species = self.get_species(species_id)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] != species.name:
            if self.repository.get_by_name(data["name"]):
                raise ConflictError("Ya existe una especie con ese nombre")
        for field, value in data.items():
            setattr(species, field, value)
        self.repository.db.commit()
        self.repository.db.refresh(species)
        return species

    def delete_species(self, species_id: int) -> None:
        species = self.get_species(species_id)
        self.repository.delete(species)
