"""Regresiones de las observaciones de QA (P20261070)."""
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.models.knowledge import FactDefinition
from app.models.species import Species
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.evaluation_service import EvaluationService
from app.core.exceptions import AppException
from tests.test_exception_handling import fixture_client as _client_fixture, fixture_db as _db_fixture  # noqa: F401

client = pytest.fixture(name="client")(_client_fixture.__wrapped__ if hasattr(_client_fixture, "__wrapped__") else _client_fixture)
db = pytest.fixture(name="db")(_db_fixture.__wrapped__ if hasattr(_db_fixture, "__wrapped__") else _db_fixture)


def test_future_birth_date_is_rejected_on_create_and_update():
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError, match="no puede ser futura"):
        PatientCreate(owner_id=1, name="Rex", species_id=1, sex="Macho", birth_date=tomorrow)
    with pytest.raises(ValidationError, match="no puede ser futura"):
        PatientUpdate(birth_date=tomorrow)


def test_today_birth_date_is_accepted():
    patient = PatientCreate(owner_id=1, name="Rex", species_id=1, sex="Macho", birth_date=date.today())
    assert patient.birth_date == date.today()


def test_negative_numeric_fact_is_rejected():
    definition = FactDefinition(fact_key="glucosa", display_name="Glucosa", data_type="numeric", source_type="clinical_variable")
    with pytest.raises(AppException, match="no puede ser negativo"):
        EvaluationService._validate_fact_value(definition, -1)
    EvaluationService._validate_fact_value(definition, 0)
    EvaluationService._validate_fact_value(definition, 12.5)


def test_validation_errors_return_string_detail_in_spanish(client):
    response = client.post("/api/v1/auth/login", json={"email": "", "password": ""})
    assert response.status_code == 422
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["detail"].startswith("Datos invalidos o incompletos")
    assert isinstance(body["errors"], list)


def test_login_with_short_password_returns_401_not_422(client):
    response = client.post("/api/v1/auth/login", json={"email": "nadie@example.com", "password": "abc"})
    assert response.status_code == 401
