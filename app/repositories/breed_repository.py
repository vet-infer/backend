from app.models.breed import Breed
from app.core.config import settings
from app.repositories.base import BaseRepository


class BreedRepository(BaseRepository[Breed]):
    model = Breed

    def get_by_name_and_species(self, name: str, species_id: int) -> Breed | None:
        return (
            self.db.query(Breed)
            .filter(Breed.name == name, Breed.species_id == species_id)
            .first()
        )

    def list_by_species(self, species_id: int, skip: int = 0, limit: int = settings.default_page_size) -> list[Breed]:
        return (
            self.db.query(Breed)
            .filter(Breed.species_id == species_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

