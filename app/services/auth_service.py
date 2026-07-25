from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets

from app.core.config import settings
from app.core.exceptions import AppException, UnauthorizedError
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)
GENERIC_RESET_MESSAGE = "Si el correo existe, recibiras instrucciones de recuperacion."


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        reset_token_repository: PasswordResetTokenRepository | None = None,
        email_service: EmailService | None = None,
    ):
        self.user_repository = user_repository
        self.reset_token_repository = reset_token_repository or PasswordResetTokenRepository(user_repository.db)
        self.email_service = email_service or EmailService()

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

    def request_password_reset(self, email: str) -> str:
        user = self.user_repository.get_by_email(email)
        if user is not None and user.is_active:
            raw_token = secrets.token_urlsafe(32)
            now = datetime.now(timezone.utc)
            expires_minutes = settings.password_reset_token_expire_minutes
            self.reset_token_repository.invalidate_active_for_user(user.id, now)
            self.reset_token_repository.create(
                PasswordResetToken(
                    user_id=user.id,
                    token_hash=self._hash_reset_token(raw_token),
                    expires_at=now + timedelta(minutes=expires_minutes),
                )
            )
            base_url = settings.frontend_base_url.rstrip("/")
            reset_url = f"{base_url}/reset-password?token={raw_token}"
            try:
                self.email_service.send_password_reset(user.email, reset_url, user.full_name)
            except Exception:
                logger.exception("No se pudo enviar el correo de recuperacion para el usuario %s", user.id)

        # Respuesta identica exista o no la cuenta, para evitar enumeracion de usuarios.
        return GENERIC_RESET_MESSAGE

    def reset_password(self, token: str, new_password: str) -> None:
        reset_token = self.reset_token_repository.get_valid_by_hash(self._hash_reset_token(token))
        if reset_token is None:
            raise UnauthorizedError("El enlace de recuperacion es invalido o ha vencido")

        user = self.user_repository.get(reset_token.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("El enlace de recuperacion es invalido o ha vencido")

        user.password_hash = get_password_hash(new_password)
        reset_token.used_at = datetime.now(timezone.utc)
        self.user_repository.db.commit()

    @staticmethod
    def _hash_reset_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
