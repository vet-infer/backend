ROLE_ADMIN = "admin"
ROLE_VETERINARIAN = "veterinario"
ROLE_EVALUATOR = "evaluador"

READ_ROLES = (ROLE_ADMIN, ROLE_VETERINARIAN, ROLE_EVALUATOR)
WRITE_ROLES = (ROLE_ADMIN, ROLE_VETERINARIAN)
ADMIN_ROLES = (ROLE_ADMIN,)

RISK_LOW = "bajo"
RISK_MODERATE = "moderado"
RISK_HIGH = "alto"

DEFAULT_RISK_LEVEL = RISK_MODERATE

RISK_LEVEL_ALIASES = {
    "low": RISK_LOW,
    "medium": RISK_MODERATE,
    "moderate": RISK_MODERATE,
    "high": RISK_HIGH,
}


def normalize_risk_level(value: str | None) -> str:
    normalized = (value or DEFAULT_RISK_LEVEL).strip().lower()
    return RISK_LEVEL_ALIASES.get(normalized, normalized)
