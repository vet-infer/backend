import httpx

from app.core.config import EMAILJS_REQUIRED_FIELDS, settings


class EmailService:
    def send_password_reset(self, recipient: str, reset_url: str, recipient_name: str | None = None) -> None:
        if not all(getattr(settings, field_name) for field_name in EMAILJS_REQUIRED_FIELDS):
            raise RuntimeError("El servicio de correo no esta configurado")

        name = recipient_name or recipient
        reset_token = reset_url.split("token=", maxsplit=1)[-1]
        payload = {
            "service_id": settings.emailjs_service_id,
            "template_id": settings.emailjs_template_id,
            "user_id": settings.emailjs_public_key,
            # La Private Key autoriza llamadas desde servidor; nunca debe exponerse al frontend.
            "accessToken": settings.emailjs_private_key,
            "template_params": {
                "to_email": recipient,
                "to_name": name,
                "user_name": name,
                "reset_url": reset_url,
                "reset_token": reset_token,
                "verification_code": reset_token,
                "expires_minutes": settings.password_reset_token_expire_minutes,
                "app_name": settings.app_name,
            },
        }

        response = httpx.post(settings.emailjs_api_url, json=payload, timeout=10)
        if response.status_code != 200:
            raise RuntimeError(f"EmailJS rechazo el envio ({response.status_code}): {response.text}")
