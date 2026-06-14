from app.models.species import Species
from app.repositories.base import BaseRepository


class SpeciesRepository(BaseRepository[Species]):
    model = Species

    def get_by_name(self, name: str) -> Species | None:
        return self.db.query(Species).filter(Species.name == name).first()
