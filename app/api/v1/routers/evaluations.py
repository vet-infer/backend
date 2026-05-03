from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.user import User
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.result_repository import ResultRepository
from app.schemas.evaluation import EvaluationCreate, EvaluationOut
from app.schemas.inference import PersistedInferenceResultOut
from app.services.evaluation_service import EvaluationService
from app.services.inference_service import InferenceService
from app.repositories.rule_repository import RuleRepository

router = APIRouter(tags=["Evaluaciones"])


def _evaluation_service(db: Session) -> EvaluationService:
    return EvaluationService(EvaluationRepository(db), PatientRepository(db))


@router.post("/evaluations", response_model=EvaluationOut, status_code=201)
def create_evaluation(
    payload: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "veterinario")),
):
    return _evaluation_service(db).create_evaluation(payload, current_user.id)


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    return _evaluation_service(db).get_evaluation(evaluation_id)


@router.get("/patients/{patient_id}/evaluations", response_model=list[EvaluationOut])
def list_patient_evaluations(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    return _evaluation_service(db).list_by_patient(patient_id)


@router.get("/evaluations/{evaluation_id}/results", response_model=list[PersistedInferenceResultOut])
def list_evaluation_results(
    evaluation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    service = InferenceService(
        RuleRepository(db),
        PatientRepository(db),
        EvaluationRepository(db),
        ResultRepository(db),
    )
    return service.list_results(evaluation_id)
