import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailService:
    def send_password_reset(self, recipient: str, reset_url: str, recipient_name: str | None = None) -> None:
        if not all((settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from_email)):
            raise RuntimeError("El servicio de correo no esta configurado")

        greeting = f"Hola {recipient_name},\n\n" if recipient_name else "Hola,\n\n"
        message = EmailMessage()
        message["Subject"] = "Restablecimiento de contrasena - VetClinic"
        message["From"] = settings.smtp_from_email
        message["To"] = recipient
        message.set_content(
            greeting
            + "Recibimos una solicitud para restablecer tu contrasena. "
            + f"Usa este enlace dentro de {settings.password_reset_token_expire_minutes} minutos: {reset_url}\n\n"
            + "Si no solicitaste este cambio, puedes ignorar este mensaje."
        )

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
            if settings.smtp_use_tls:
                client.starttls()
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)