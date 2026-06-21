from app.core.exceptions import ConflictError, NotFoundError, ForbiddenError
from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


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

    def update_user(self, user_id: int, payload: UserUpdate, current_user_id: int | None = None) -> User:
        user = self.repository.get_with_role(user_id)
        if not user:
            raise NotFoundError("Usuario no encontrado")

        if payload.email and payload.email != user.email:
            existing = self.repository.get_by_email(payload.email)
            if existing and existing.id != user_id:
                raise ConflictError("Ya existe un usuario con ese correo")
            user.email = payload.email

        if payload.role_id is not None:
            if not self.repository.role_exists(payload.role_id):
                raise NotFoundError("Rol no encontrado")
            user.role_id = payload.role_id

        if payload.full_name is not None:
            user.full_name = payload.full_name

        if payload.password is not None:
            user.password_hash = get_password_hash(payload.password)

        if payload.is_active is not None:
            if current_user_id == user_id and payload.is_active is False:
                raise ForbiddenError("No puedes desactivar tu propio usuario")
            user.is_active = payload.is_active

        return self.repository.save(user)
