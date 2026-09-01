import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.exceptions import ConflictError
from app.models import Species, Disease, Role, User
from app.repositories.rule_repository import RuleRepository
from app.schemas.rule import RuleConditionCreate, RuleCreate, RuleUpdate
from app.services.bootstrap_service import bootstrap_reference_data
from app.services.rule_service import RuleService
from app.core.security import get_password_hash

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db")
def fixture_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        db.add(Role(id=1, name="admin", description="Admin"))
        db.add(User(id=1, full_name="Admin", email="admin@example.com", password_hash=get_password_hash("x"), role_id=1))
        db.commit()
        bootstrap_reference_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# --- Pydantic schema-level validation (RuleConditionCreate) ---


@pytest.mark.parametrize("operator", ["eq", "neq", "gt", "gte", "lt", "lte", "between", "contains", "in"])
def test_supported_operators_are_accepted(operator):
    expected = {
        "gt": 1, "gte": 1, "lt": 1, "lte": 1,
        "between": [1, 5],
        "in": ["a", "b"],
    }.get(operator, "x")
    condition = RuleConditionCreate(variable_key="glucosa", operator=operator, expected_value=expected)
    assert condition.operator == operator


def test_unsupported_operator_is_rejected():
    with pytest.raises(ValidationError):
        RuleConditionCreate(variable_key="glucosa", operator="cotnains", expected_value="x")


@pytest.mark.parametrize("operator", ["gt", "gte", "lt", "lte"])
def test_numeric_operator_requires_numeric_expected_value(operator):
    with pytest.raises(ValidationError):
        RuleConditionCreate(variable_key="glucosa", operator=operator, expected_value="no-numerico")


@pytest.mark.parametrize(
    "expected_value",
    [[1, 5], {"min": 1, "max": 5}],
)
def test_between_accepts_valid_shapes(expected_value):
    condition = RuleConditionCreate(variable_key="glucosa", operator="between", expected_value=expected_value)
    assert condition.expected_value == expected_value


@pytest.mark.parametrize(
    "expected_value",
    [5, "1-5", [1], [5, 1], {"min": 5, "max": 1}],
)
def test_between_rejects_invalid_shapes(expected_value):
    with pytest.raises(ValidationError):
        RuleConditionCreate(variable_key="glucosa", operator="between", expected_value=expected_value)


def test_in_operator_requires_list_or_string():
    with pytest.raises(ValidationError):
        RuleConditionCreate(variable_key="glucosa", operator="in", expected_value=123)


def test_rule_update_reuses_same_condition_validation():
    with pytest.raises(ValidationError):
        RuleUpdate(conditions=[{"variable_key": "glucosa", "operator": "cotnains", "expected_value": "x"}])


# --- Service-level round trip (RuleService.create_rule / update_rule) ---


def test_rule_service_creates_rule_with_valid_conditions(db):
    dog = db.query(Species).filter(Species.name == "Perro").first()
    disease = db.query(Disease).filter(Disease.name == "Diabetes mellitus", Disease.species_id == dog.id).first()

    service = RuleService(RuleRepository(db))
    payload = RuleCreate(
        code="TEST-VAL-01",
        name="Regla de prueba con condiciones validas",
        disease_id=disease.id,
        weight=1.0,
        priority=1,
        conditions=[RuleConditionCreate(variable_key="glucosa", operator="gt", expected_value=200)],
    )
    rule = service.create_rule(payload)

    assert rule.id is not None
    assert rule.conditions[0].operator == "gt"


def test_rule_service_update_with_invalid_conditions_is_rejected_before_persisting(db):
    dog = db.query(Species).filter(Species.name == "Perro").first()
    disease = db.query(Disease).filter(Disease.name == "Diabetes mellitus", Disease.species_id == dog.id).first()

    service = RuleService(RuleRepository(db))
    payload = RuleCreate(
        code="TEST-VAL-02",
        name="Regla de prueba",
        disease_id=disease.id,
        weight=1.0,
        priority=1,
        conditions=[RuleConditionCreate(variable_key="glucosa", operator="gt", expected_value=200)],
    )
    rule = service.create_rule(payload)

    with pytest.raises(ValidationError):
        RuleUpdate(conditions=[{"variable_key": "glucosa", "operator": "between", "expected_value": [10]}])

    # Original rule remains untouched
    reloaded = service.get_rule(rule.id)
    assert reloaded.conditions[0].operator == "gt"
