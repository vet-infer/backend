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


def test_rate_limit_settings_default_values(monkeypatch):
    # conftest.py forces RATE_LIMIT_ENABLED=false as a real env var for the whole
    # test session (so the limiter stays off everywhere except the tests that
    # override it explicitly) - unset it here to observe the field's true default.
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)

    settings = Settings(_env_file=None)

    assert settings.rate_limit_enabled is True
    assert settings.rate_limit_login == "10/minute"
    assert settings.rate_limit_inference == "30/minute"


def test_rate_limit_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "5/minute")
    monkeypatch.setenv("RATE_LIMIT_INFERENCE", "20/minute")

    settings = Settings(_env_file=None)

    assert settings.rate_limit_enabled is False
    assert settings.rate_limit_login == "5/minute"
    assert settings.rate_limit_inference == "20/minute"
