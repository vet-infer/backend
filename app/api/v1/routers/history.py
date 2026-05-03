from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.user import User
from app.repositories.history_repository import HistoryRepository
from app.schemas.inference import ClinicalHistoryOut
from app.services.history_service import HistoryService

router = APIRouter(prefix="/patients", tags=["Historial clinico"])


@router.get("/{patient_id}/history", response_model=list[ClinicalHistoryOut])
def list_patient_history(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    return HistoryService(HistoryRepository(db)).list_by_patient(patient_id)
