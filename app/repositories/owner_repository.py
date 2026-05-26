from app.models.owner import Owner
from app.repositories.base import BaseRepository


class OwnerRepository(BaseRepository[Owner]):
    model = Owner

    def get_by_email(self, email: str) -> Owner | None:
        return self.db.query(Owner).filter(Owner.email == email).first()

    def get_by_id(self, owner_id: int) -> Owner | None:
        return self.get(owner_id)

    def create(self, data: dict) -> Owner:
        return self.add(Owner(**data))

    def update(self, owner_id: int, data: dict) -> Owner | None:
        owner = self.get(owner_id)
        if owner is None:
            return None
        for field, value in data.items():
            setattr(owner, field, value)
        self.db.commit()
        self.db.refresh(owner)
        return owner

    def delete(self, owner_id: int) -> None:
        owner = self.get(owner_id)
        if owner is not None:
            super().delete(owner)
