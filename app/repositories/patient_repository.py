from sqlalchemy.orm import joinedload

from app.models.owner import Owner
from app.models.patient import Patient, Species
from app.repositories.base import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    model = Patient

    def get_with_species(self, patient_id: int) -> Patient | None:
        return (
            self.db.query(Patient)
            .options(joinedload(Patient.species), joinedload(Patient.owner))
            .filter(Patient.id == patient_id)
            .first()
        )

    def list_with_species(self, skip: int = 0, limit: int = 100) -> list[Patient]:
        return (
            self.db.query(Patient)
            .options(joinedload(Patient.species), joinedload(Patient.owner))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def species_exists(self, species_id: int) -> bool:
        return self.db.get(Species, species_id) is not None

    def owner_exists(self, owner_id: int) -> bool:
        return self.db.get(Owner, owner_id) is not None
