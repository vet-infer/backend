from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Motor de Inferencia Veterinario"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    database_url: str = "sqlite:///./oe3_runtime.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    password_reset_token_expire_minutes: int = 15
    frontend_base_url: str = "http://localhost:5173"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    cors_origins: list[str] = []
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    default_page_size: int = 50
    # El catalogo de razas contiene varios cientos de registros por especie.
    # Debe poder cargarse completo en los formularios que ofrecen busqueda local.
    max_page_size: int = 500
    bayes_default_prior: float = 0.20
    bayes_smoothing_factor: float = 0.50
    probability_precision: int = 4
    inference_high_score_threshold: float = 7.0
    inference_moderate_score_threshold: float = 4.0
    seed_data_path: Path = Path("app/seeds/clinical_reference_data.json")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def normalize_and_validate_settings(self) -> "Settings":
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)

        if self.environment.lower() in {"production", "prod"}:
            if self._is_local_frontend_url(self.frontend_base_url):
                public_origin = self._first_public_cors_origin()
                if public_origin:
                    self.frontend_base_url = public_origin

            insecure_jwt_values = {"dev-only-change-me", "change-me-in-production", "change-this-secret"}
            if self.jwt_secret in insecure_jwt_values:
                raise ValueError("JWT_SECRET debe configurarse con un secreto seguro en produccion.")
            if not self.cors_origins:
                raise ValueError("CORS_ORIGINS debe configurarse explicitamente en produccion.")
            if self.database_url.startswith("sqlite"):
                raise ValueError("DATABASE_URL debe apuntar a PostgreSQL en produccion.")
            smtp_settings = {
                "SMTP_HOST": self.smtp_host,
                "SMTP_USERNAME": self.smtp_username,
                "SMTP_PASSWORD": self.smtp_password,
                "SMTP_FROM_EMAIL": self.smtp_from_email,
            }
            configured_smtp_settings = [name for name, value in smtp_settings.items() if value]
            if configured_smtp_settings and len(configured_smtp_settings) != len(smtp_settings):
                missing_smtp_settings = [name for name, value in smtp_settings.items() if not value]
                raise ValueError(
                    "SMTP debe configurarse completamente o dejarse deshabilitado. Faltan: "
                    + ", ".join(missing_smtp_settings)
                )
            if self._is_local_frontend_url(self.frontend_base_url):
                raise ValueError("FRONTEND_BASE_URL debe usar el dominio publico en produccion.")
        return self

    def _first_public_cors_origin(self) -> str | None:
        for origin in self.cors_origins:
            normalized_origin = origin.rstrip("/")
            if normalized_origin.startswith("https://") and not self._is_local_frontend_url(normalized_origin):
                return normalized_origin
        return None

    @staticmethod
    def _is_local_frontend_url(url: str) -> bool:
        return "localhost" in url or "127.0.0.1" in url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
