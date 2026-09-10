from app.models.anatomical_region import AnatomicalRegion
from app.repositories.base import BaseRepository


class AnatomicalRegionRepository(BaseRepository[AnatomicalRegion]):
    model = AnatomicalRegion

    def get_by_code(self, code: str) -> AnatomicalRegion | None:
        return self.db.query(AnatomicalRegion).filter(AnatomicalRegion.code == code).first()
