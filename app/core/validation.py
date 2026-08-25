import re
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_email_format(email: str) -> str:
    normalized_email = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized_email):
        raise ValueError("Correo electronico invalido")
    return normalized_email


def _validate_optional_email(value: str | None) -> str | None:
    if value:
        return validate_email_format(value)
    return value


def _normalize_optional_text(value: str | None) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return value


RequiredEmail = Annotated[str, Field(min_length=3, max_length=255), AfterValidator(validate_email_format)]
OptionalEmail = Annotated[
    str | None, Field(default=None, min_length=3, max_length=255), AfterValidator(_validate_optional_email)
]
OptionalNormalizedText = Annotated[str | None, BeforeValidator(_normalize_optional_text)]
