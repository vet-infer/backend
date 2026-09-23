import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.exceptions import ConflictError
from app.models.owner import Owner
from app.repositories.owner_repository import OwnerRepository
from app.schemas.owner import DocumentType, OwnerCreate, OwnerUpdate
from app.services.owner_service import OwnerService

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db")
def fixture_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def make_owner_payload(**overrides):
    payload = {
        "first_name": "Maria",
        "last_name": "Garcia",
        "phone": "+51999000111",
        "email": "maria@example.com",
        "document_type": DocumentType.DNI,
        "document_number": "12345678",
        "address": "Av. Siempreviva 742",
    }
    payload.update(overrides)
    return payload


def test_dni_valid_format_accepted():
    schema = OwnerCreate(**make_owner_payload())
    assert schema.document_number == "12345678"


@pytest.mark.parametrize("document_number", ["1234567", "123456789", "1234A678"])
def test_dni_invalid_format_rejected(document_number):
    with pytest.raises(ValidationError):
        OwnerCreate(**make_owner_payload(document_number=document_number))


def test_ce_and_passport_accept_alphanumeric_up_to_12_chars():
    schema = OwnerCreate(**make_owner_payload(document_type=DocumentType.CE, document_number="AB123456789"))
    assert schema.document_number == "AB123456789"

    schema = OwnerCreate(**make_owner_payload(document_type=DocumentType.PASSPORT, document_number="P1234567"))
    assert schema.document_number == "P1234567"


def test_ce_or_passport_rejects_more_than_12_chars():
    with pytest.raises(ValidationError):
        OwnerCreate(**make_owner_payload(document_type=DocumentType.CE, document_number="123456789012A"))


def test_document_type_and_number_required_together():
    with pytest.raises(ValidationError):
        OwnerCreate(**make_owner_payload(document_number=None))


def test_owner_without_document_is_allowed():
    schema = OwnerCreate(**make_owner_payload(document_type=None, document_number=None))
    assert schema.document_type is None
    assert schema.document_number is None


def test_create_owner_rejects_duplicate_document(db):
    service = OwnerService(OwnerRepository(db))

    service.create_owner(OwnerCreate(**make_owner_payload()))

    with pytest.raises(ConflictError):
        service.create_owner(
            OwnerCreate(**make_owner_payload(email="otro@example.com", first_name="Otro"))
        )


def test_create_owner_allows_same_email_different_document(db):
    service = OwnerService(OwnerRepository(db))

    service.create_owner(OwnerCreate(**make_owner_payload()))
    second = service.create_owner(
        OwnerCreate(**make_owner_payload(document_number="87654321", first_name="Otro"))
    )

    assert second.id is not None
    assert second.email == "maria@example.com"


def test_update_owner_rejects_document_used_by_another(db):
    service = OwnerService(OwnerRepository(db))

    first = service.create_owner(OwnerCreate(**make_owner_payload()))
    second = service.create_owner(
        OwnerCreate(**make_owner_payload(document_number="87654321", first_name="Otro"))
    )

    with pytest.raises(ConflictError):
        service.update_owner(
            second.id,
            OwnerUpdate(document_type=DocumentType.DNI, document_number="12345678"),
        )

    assert first.document_number == "12345678"


def test_repository_create_blocks_duplicate_document_inserted_outside_service(db):
    """Simula una condicion de carrera: un registro se inserta directo en la BD
    (sin pasar por el chequeo optimista del servicio) y una segunda insercion
    con el mismo documento, via el repositorio, debe seguir siendo bloqueada
    por la constraint unica de la base de datos."""
    db.add(Owner(first_name="Directo", document_type="DNI", document_number="55555555"))
    db.commit()

    repository = OwnerRepository(db)
    with pytest.raises(ConflictError):
        repository.create({"first_name": "Via Repo", "document_type": "DNI", "document_number": "55555555"})
