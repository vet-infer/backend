from typing import Any


def normalize_facts(raw_facts: dict[str, Any]) -> dict[str, Any]:
    return {key.strip(): value for key, value in raw_facts.items() if key and value is not None}
