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
    cors_origins: list[str] = []
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    default_page_size: int = 50
    max_page_size: int = 100
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
            insecure_jwt_values = {"dev-only-change-me", "change-me-in-production", "change-this-secret"}
            if self.jwt_secret in insecure_jwt_values:
                raise ValueError("JWT_SECRET debe configurarse con un secreto seguro en produccion.")
            if not self.cors_origins:
                raise ValueError("CORS_ORIGINS debe configurarse explicitamente en produccion.")
            if self.database_url.startswith("sqlite"):
                raise ValueError("DATABASE_URL debe apuntar a PostgreSQL en produccion.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
