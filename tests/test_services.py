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
from app.core.exceptions import NotFoundError, ConflictError, AppException

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
