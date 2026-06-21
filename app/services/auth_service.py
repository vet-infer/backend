from app.core.exceptions import AppException, UnauthorizedError
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def login(self, email: str, password: str) -> TokenResponse:
        user = self.user_repository.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Credenciales invalidas")
        if not user.is_active:
            raise UnauthorizedError("Usuario inactivo")

        role_name = user.role.name if user.role else "veterinario"
        token = create_access_token(subject=str(user.id), role=role_name)
        return TokenResponse(access_token=token)

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedError("La contrasena actual es incorrecta")

        if current_password == new_password:
            raise AppException("La nueva contrasena debe ser diferente de la actual")

        user.password_hash = get_password_hash(new_password)
        self.user_repository.save(user)
