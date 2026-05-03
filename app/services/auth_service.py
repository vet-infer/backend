from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, verify_password
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
