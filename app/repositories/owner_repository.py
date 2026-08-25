from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError
from app.models.owner import Owner
from app.repositories.base import BaseRepository


class OwnerRepository(BaseRepository[Owner]):
    model = Owner

    def get_by_email(self, email: str) -> Owner | None:
        return self.db.query(Owner).filter(Owner.email == email).first()

    def get_by_id(self, owner_id: int) -> Owner | None:
        return self.get(owner_id)

    def create(self, data: dict) -> Owner:
        try:
            return self.add(Owner(**data))
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("El correo ya esta registrado") from exc

    def update_by_id(self, owner_id: int, data: dict) -> Owner | None:
        owner = self.get(owner_id)
        if owner is None:
            return None
        try:
            return self.update(owner, data)
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("El correo ya esta registrado") from exc

    def delete(self, owner_id: int) -> None:
        owner = self.get(owner_id)
        if owner is not None:
            super().delete(owner)
