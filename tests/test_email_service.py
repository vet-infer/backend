import httpx
import pytest

from app.core.config import settings
from app.services import email_service as email_service_module
from app.services.email_service import EmailService


@pytest.fixture
def emailjs_settings(monkeypatch):
    monkeypatch.setattr(settings, "emailjs_service_id", "service_test")
    monkeypatch.setattr(settings, "emailjs_template_id", "template_test")
    monkeypatch.setattr(settings, "emailjs_public_key", "public_test")
    monkeypatch.setattr(settings, "emailjs_private_key", "private_test")


def test_send_password_reset_posts_to_emailjs_with_private_key(monkeypatch, emailjs_settings):
    calls = []

    def fake_post(url, json, timeout):
        calls.append((url, json))
        return httpx.Response(200, text="OK")

    monkeypatch.setattr(email_service_module.httpx, "post", fake_post)

    EmailService().send_password_reset("user@example.test", "http://front/reset-password?token=abc123", "Ana")

    assert len(calls) == 1
    url, payload = calls[0]
    assert url == settings.emailjs_api_url
    assert payload["service_id"] == "service_test"
    assert payload["accessToken"] == "private_test"
    assert payload["template_params"]["to_email"] == "user@example.test"
    assert payload["template_params"]["reset_token"] == "abc123"


def test_send_password_reset_raises_when_emailjs_rejects(monkeypatch, emailjs_settings):
    monkeypatch.setattr(
        email_service_module.httpx, "post", lambda url, json, timeout: httpx.Response(403, text="forbidden")
    )

    with pytest.raises(RuntimeError, match="EmailJS rechazo el envio \\(403\\)"):
        EmailService().send_password_reset("user@example.test", "http://front/reset-password?token=abc123")


def test_send_password_reset_requires_configuration(monkeypatch):
    monkeypatch.setattr(settings, "emailjs_private_key", None)

    with pytest.raises(RuntimeError, match="no esta configurado"):
        EmailService().send_password_reset("user@example.test", "http://front/reset-password?token=abc123")


def test_send_account_created_posts_credentials_with_welcome_template(monkeypatch, emailjs_settings):
    monkeypatch.setattr(settings, "emailjs_welcome_template_id", "welcome_test")
    calls = []

    def fake_post(url, json, timeout):
        calls.append(json)
        return httpx.Response(200, text="OK")

    monkeypatch.setattr(email_service_module.httpx, "post", fake_post)

    EmailService().send_account_created("user@example.test", "Clave1234", "Ana")

    assert len(calls) == 1
    payload = calls[0]
    assert payload["template_id"] == "welcome_test"
    assert payload["template_params"]["to_email"] == "user@example.test"
    assert payload["template_params"]["email"] == "user@example.test"
    assert payload["template_params"]["password"] == "Clave1234"
    assert payload["template_params"]["login_url"].endswith("/login")


def test_send_account_created_requires_welcome_template(monkeypatch, emailjs_settings):
    monkeypatch.setattr(settings, "emailjs_welcome_template_id", None)

    with pytest.raises(RuntimeError, match="bienvenida no esta configurado"):
        EmailService().send_account_created("user@example.test", "Clave1234")
