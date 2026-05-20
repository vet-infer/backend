from app.core.exceptions import NotFoundError
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreate, PatientUpdate


class PatientService:
    def __init__(self, repository: PatientRepository):
        self.repository = repository

    def list_patients(self) -> list[Patient]:
        return self.repository.list_with_species()

    def get_patient(self, patient_id: int) -> Patient:
        patient = self.repository.get_with_species(patient_id)
        if patient is None:
            raise NotFoundError("Paciente no encontrado")
        return patient

    def create_patient(self, payload: PatientCreate, created_by: int) -> Patient:
        if not self.repository.species_exists(payload.species_id):
            raise NotFoundError("Especie no encontrada")
        if not self.repository.owner_exists(payload.owner_id):
            raise NotFoundError("Dueño no encontrado")
        patient = Patient(**payload.model_dump(), created_by=created_by)
        return self.repository.add(patient)

    def update_patient(self, patient_id: int, payload: PatientUpdate) -> Patient:
        patient = self.get_patient(patient_id)
        data = payload.model_dump(exclude_unset=True)
        if "species_id" in data and not self.repository.species_exists(data["species_id"]):
            raise NotFoundError("Especie no encontrada")
        if "owner_id" in data and not self.repository.owner_exists(data["owner_id"]):
            raise NotFoundError("Dueño no encontrado")
        for field, value in data.items():
            setattr(patient, field, value)
        self.repository.db.commit()
        self.repository.db.refresh(patient)
        return patient
