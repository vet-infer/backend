from sqlalchemy.orm import Session, joinedload

from app.models.role import Role
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return (
            self.db.query(User)
            .options(joinedload(User.role))
            .filter(User.email == email)
            .first()
        )

    def list_with_roles(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.db.query(User).options(joinedload(User.role)).offset(skip).limit(limit).all()

    def role_exists(self, role_id: int) -> bool:
        return self.db.get(Role, role_id) is not None

    def ensure_default_roles(self) -> None:
        for name, description in [
            ("admin", "Administrador del sistema"),
            ("veterinario", "Medico veterinario"),
            ("evaluador", "Asesor o evaluador academico"),
        ]:
            if self.db.query(Role).filter(Role.name == name).first() is None:
                self.db.add(Role(name=name, description=description))
        self.db.commit()
