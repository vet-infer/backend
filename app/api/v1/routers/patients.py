from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreate, PatientOut, PatientUpdate
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Pacientes"])


@router.get("", response_model=list[PatientOut])
def list_patients(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    return PatientService(PatientRepository(db)).list_patients()


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "veterinario")),
):
    return PatientService(PatientRepository(db)).create_patient(payload, current_user.id)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    return PatientService(PatientRepository(db)).get_patient(patient_id)


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario")),
):
    return PatientService(PatientRepository(db)).update_patient(patient_id, payload)
