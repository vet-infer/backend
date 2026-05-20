from app.models.owner import Owner
from app.repositories.base import BaseRepository


class OwnerRepository(BaseRepository[Owner]):
    model = Owner

    def get_by_email(self, email: str) -> Owner | None:
        return self.db.query(Owner).filter(Owner.email == email).first()
