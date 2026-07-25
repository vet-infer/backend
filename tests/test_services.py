import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.species import Species
from app.models.breed import Breed
from app.models.owner import Owner
from app.models.patient import Patient
from app.models.role import Role
from app.models.user import User
from app.repositories.species_repository import SpeciesRepository
from app.repositories.breed_repository import BreedRepository
from app.repositories.patient_repository import PatientRepository
from app.services.species_service import SpeciesService
from app.services.breed_service import BreedService
from app.services.patient_service import PatientService
from app.schemas.species import SpeciesCreate, SpeciesUpdate
from app.schemas.breed import BreedCreate, BreedUpdate
from app.schemas.patient import PatientCreate, PatientUpdate
from app.core.exceptions import NotFoundError, ConflictError, AppException, UnauthorizedError
from app.core.security import get_password_hash, verify_password
from app.repositories.user_repository import UserRepository
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.services.auth_service import AuthService

TEST_ADMIN_EMAIL = "test-admin@example.test"

# Set up SQLite in-memory database
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db")
def fixture_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Create default roles
        admin_role = Role(id=1, name="admin", description="Admin")
        db.add(admin_role)
        # Create a default user
        user = User(id=1, full_name="Admin", email=TEST_ADMIN_EMAIL, password_hash="hash", role_id=1)
        db.add(user)
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_species_service(db):
    species_repo = SpeciesRepository(db)
    species_service = SpeciesService(species_repo)

    # 1. Create species
    sp = species_service.create_species(SpeciesCreate(name="Perro"))
    assert sp.id is not None
    assert sp.name == "Perro"

    # 2. Duplicate species conflict
    with pytest.raises(ConflictError):
        species_service.create_species(SpeciesCreate(name="Perro"))

    # 3. List species
    all_sp = species_service.list_species()
    assert len(all_sp) == 1
    assert all_sp[0].name == "Perro"

    # 4. Get species
    retrieved = species_service.get_species(sp.id)
    assert retrieved.name == "Perro"

    # 5. Update species
    updated = species_service.update_species(sp.id, SpeciesUpdate(name="Canino"))
    assert updated.name == "Canino"

    # 6. Delete species
    species_service.delete_species(sp.id)
    with pytest.raises(NotFoundError):
        species_service.get_species(sp.id)


def test_breed_service(db):
    species_repo = SpeciesRepository(db)
    species_service = SpeciesService(species_repo)
    breed_repo = BreedRepository(db)
    breed_service = BreedService(breed_repo)

    # Create species
    sp = species_service.create_species(SpeciesCreate(name="Perro"))

    # 1. Create breed
    br = breed_service.create_breed(BreedCreate(name="Poodle", species_id=sp.id))
    assert br.id is not None
    assert br.name == "Poodle"
    assert br.species_id == sp.id

    # 2. Duplicate breed under same species conflict
    with pytest.raises(ConflictError):
        breed_service.create_breed(BreedCreate(name="Poodle", species_id=sp.id))

    # 3. Create same breed under different species (should pass)
    sp2 = species_service.create_species(SpeciesCreate(name="Gato"))
    br2 = breed_service.create_breed(BreedCreate(name="Poodle", species_id=sp2.id))
    assert br2.id is not None
    assert br2.species_id == sp2.id

    # 4. Get breed
    retrieved = breed_service.get_breed(br.id)
    assert retrieved.name == "Poodle"

    # 5. List breeds by species
    dog_breeds = breed_service.list_breeds(species_id=sp.id)
    assert len(dog_breeds) == 1
    assert dog_breeds[0].name == "Poodle"

    # 6. Update breed
    updated = breed_service.update_breed(br.id, BreedUpdate(name="Standard Poodle"))
    assert updated.name == "Standard Poodle"

    # 7. Delete breed
    breed_service.delete_breed(br.id)
    with pytest.raises(NotFoundError):
        breed_service.get_breed(br.id)


def test_patient_service_validation(db):
    species_repo = SpeciesRepository(db)
    breed_repo = BreedRepository(db)
    patient_repo = PatientRepository(db)
    
    species_service = SpeciesService(species_repo)
    breed_service = BreedService(breed_repo)
    patient_service = PatientService(patient_repo)

    # Setup database elements
    dog = species_service.create_species(SpeciesCreate(name="Perro"))
    cat = species_service.create_species(SpeciesCreate(name="Gato"))

    poodle = breed_service.create_breed(BreedCreate(name="Poodle", species_id=dog.id))
    siamese = breed_service.create_breed(BreedCreate(name="Siamés", species_id=cat.id))

    # Create an owner
    owner = Owner(first_name="Juan", last_name="Perez", email="juan@example.com")
    db.add(owner)
    db.commit()
    db.refresh(owner)

    # 1. Create patient with matching breed and species (Perro & Poodle) -> OK
    patient_payload = PatientCreate(
        owner_id=owner.id,
        name="Bobby",
        species_id=dog.id,
        breed_id=poodle.id,
        sex="Macho",
        birth_date=None,
        weight=10.0
    )
    patient = patient_service.create_patient(patient_payload, created_by=1)
    assert patient.id is not None
    assert patient.name == "Bobby"
    assert patient.breed_id == poodle.id
    assert patient.species_id == dog.id

    # 2. Create patient with mismatching breed and species (Gato & Poodle) -> ERROR
    mismatch_payload = PatientCreate(
        owner_id=owner.id,
        name="Michi",
        species_id=cat.id,
        breed_id=poodle.id,  # Poodle belongs to dog!
        sex="Macho",
        birth_date=None,
        weight=4.0
    )
    with pytest.raises(AppException) as excinfo:
        patient_service.create_patient(mismatch_payload, created_by=1)
    assert "La raza no pertenece a la especie seleccionada" in str(excinfo.value.detail)

    # 3. Create patient with non-existent breed_id -> ERROR
    non_existent_breed_payload = PatientCreate(
        owner_id=owner.id,
        name="Michi",
        species_id=cat.id,
        breed_id=999,
        sex="Macho",
        birth_date=None,
        weight=4.0
    )
    with pytest.raises(NotFoundError):
        patient_service.create_patient(non_existent_breed_payload, created_by=1)

    # 4. Update patient to mismatched breed -> ERROR
    update_payload = PatientUpdate(breed_id=siamese.id)  # Siamese belongs to Gato, but Bobby is a Perro!
    with pytest.raises(AppException) as excinfo:
        patient_service.update_patient(patient.id, update_payload)
    assert "La raza no pertenece a la especie seleccionada" in str(excinfo.value.detail)


def test_change_password_requires_current_password_and_persists_new_hash(db):
    user = db.query(User).filter(User.email == TEST_ADMIN_EMAIL).one()
    user.password_hash = get_password_hash("ContrasenaInicial1")
    db.commit()

    auth_service = AuthService(UserRepository(db))

    with pytest.raises(UnauthorizedError):
        auth_service.change_password(user, "Incorrecta1", "ContrasenaNueva1")

    with pytest.raises(AppException, match="diferente"):
        auth_service.change_password(user, "ContrasenaInicial1", "ContrasenaInicial1")

    auth_service.change_password(user, "ContrasenaInicial1", "ContrasenaNueva1")
    db.refresh(user)

    assert verify_password("ContrasenaNueva1", user.password_hash)
    assert not verify_password("ContrasenaInicial1", user.password_hash)


class FakeEmailService:
    def __init__(self):
        self.messages: list[tuple[str, str]] = []

    def send_password_reset(self, recipient: str, reset_url: str, recipient_name: str | None = None) -> None:
        self.messages.append((recipient, reset_url))


def test_password_recovery_sends_single_use_token_and_resets_password(db):
    user = db.query(User).filter(User.email == TEST_ADMIN_EMAIL).one()
    user.password_hash = get_password_hash("ContrasenaInicial1")
    db.commit()
    email_service = FakeEmailService()
    auth_service = AuthService(
        UserRepository(db),
        PasswordResetTokenRepository(db),
        email_service,
    )

    message = auth_service.request_password_reset(TEST_ADMIN_EMAIL)
    assert "Si el correo existe" in message
    assert len(email_service.messages) == 1
    token = email_service.messages[0][1].split("token=", maxsplit=1)[1]

    auth_service.reset_password(token, "ContrasenaNueva1")
    db.refresh(user)
    assert verify_password("ContrasenaNueva1", user.password_hash)

    with pytest.raises(UnauthorizedError):
        auth_service.reset_password(token, "OtraContrasena1")


def test_password_recovery_returns_generic_message_for_unknown_email(db):
    email_service = FakeEmailService()
    auth_service = AuthService(
        UserRepository(db),
        PasswordResetTokenRepository(db),
        email_service,
    )

    message = auth_service.request_password_reset("no-registrado@example.test")
    assert "Si el correo existe" in message
    assert len(email_service.messages) == 0
