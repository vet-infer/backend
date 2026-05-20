from app.core.exceptions import ConflictError, NotFoundError
from app.models.breed import Breed
from app.repositories.breed_repository import BreedRepository
from app.repositories.species_repository import SpeciesRepository
from app.schemas.breed import BreedCreate, BreedUpdate


class BreedService:
    def __init__(self, repository: BreedRepository):
        self.repository = repository

    def list_breeds(self, species_id: int | None = None, skip: int = 0, limit: int = 100) -> list[Breed]:
        if species_id is not None:
            return self.repository.list_by_species(species_id, skip=skip, limit=limit)
        return self.repository.list(skip=skip, limit=limit)

    def get_breed(self, breed_id: int) -> Breed:
        breed = self.repository.get(breed_id)
        if breed is None:
            raise NotFoundError("Raza no encontrada")
        return breed

    def create_breed(self, payload: BreedCreate) -> Breed:
        # Verify species exists
        species_repo = SpeciesRepository(self.repository.db)
        if not species_repo.get(payload.species_id):
            raise NotFoundError("Especie no encontrada")

        # Verify uniqueness
        if self.repository.get_by_name_and_species(payload.name, payload.species_id):
            raise ConflictError("Ya existe esta raza para la especie seleccionada")

        breed = Breed(**payload.model_dump())
        return self.repository.add(breed)

    def update_breed(self, breed_id: int, payload: BreedUpdate) -> Breed:
        breed = self.get_breed(breed_id)
        data = payload.model_dump(exclude_unset=True)

        species_id = data.get("species_id", breed.species_id)
        name = data.get("name", breed.name)

        if "species_id" in data:
            species_repo = SpeciesRepository(self.repository.db)
            if not species_repo.get(data["species_id"]):
                raise NotFoundError("Especie no encontrada")

        if "name" in data or "species_id" in data:
            existing = self.repository.get_by_name_and_species(name, species_id)
            if existing and existing.id != breed_id:
                raise ConflictError("Ya existe esta raza para la especie seleccionada")

        for field, value in data.items():
            setattr(breed, field, value)
        self.repository.db.commit()
        self.repository.db.refresh(breed)
        return breed

    def delete_breed(self, breed_id: int) -> None:
        breed = self.get_breed(breed_id)
        self.repository.delete(breed)
