import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides):
    values = {
        "environment": "production",
        "database_url": "postgresql+psycopg://user:password@db.example:5432/oe3",
        "jwt_secret": "test-production-secret",
        "cors_origins": ["https://frontend.example"],
    }
    values.update(overrides)
    return Settings(**values)


def test_production_allows_smtp_to_be_disabled():
    settings = production_settings()

    assert settings.smtp_host is None


def test_production_uses_public_cors_origin_when_frontend_base_url_is_local():
    settings = production_settings(
        frontend_base_url="http://localhost:5173",
        cors_origins=["https://frontend.example", "http://localhost:5173"],
    )

    assert settings.frontend_base_url == "https://frontend.example"


def test_production_rejects_local_frontend_base_url_without_public_origin():
    with pytest.raises(ValidationError, match="FRONTEND_BASE_URL debe usar el dominio publico"):
        production_settings(
            frontend_base_url="http://localhost:5173",
            cors_origins=["http://localhost:5173"],
        )


def test_production_rejects_partial_smtp_configuration():
    with pytest.raises(ValidationError, match="SMTP debe configurarse completamente"):
        production_settings(smtp_host="smtp.example")
