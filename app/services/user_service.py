from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def list_users(self) -> list[User]:
        return self.repository.list_with_roles()

    def create_user(self, payload: UserCreate) -> User:
        if self.repository.get_by_email(payload.email):
            raise ConflictError("Ya existe un usuario con ese correo")
        if not self.repository.role_exists(payload.role_id):
            raise NotFoundError("Rol no encontrado")

        user = User(
            full_name=payload.full_name,
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            role_id=payload.role_id,
        )
        return self.repository.add(user)
