from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PermissionPolicy, require_policy
from app.models.user import User
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.result_repository import ResultRepository
from app.repositories.rule_repository import RuleRepository
from app.schemas.inference import (
    InferenceRequest,
    InferenceResultOut,
    PersistedActivatedRuleOut,
    PersistedInferenceResultOut,
)
from app.services.inference_service import InferenceService

router = APIRouter(prefix="/inference", tags=["Inferencia"])


def _service(db: Session) -> InferenceService:
    return InferenceService(
        RuleRepository(db),
        PatientRepository(db),
        EvaluationRepository(db),
        ResultRepository(db),
    )


@router.post("/run", response_model=list[InferenceResultOut])
def run_inference(
    payload: InferenceRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    facts = {fact.key: fact.value for fact in payload.facts}
    return _service(db).run_from_payload(payload.patient_id, facts)


@router.post(
    "/evaluations/{evaluation_id}/run",
    response_model=list[PersistedInferenceResultOut],
    deprecated=True,
    summary="[Obsoleto] Ejecutar y persistir inferencia para una evaluacion",
    description=(
        "Obsoleto: usar POST /evaluaciones/{evaluation_id}/procesar, el endpoint "
        "canonico (contrato en espanol). Este endpoint se mantiene sin cambios "
        "funcionales por compatibilidad; ambos delegan en InferenceService.run_and_persist."
    ),
)
def run_inference_for_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    return _service(db).run_and_persist(evaluation_id)


@router.get("/results/{result_id}/activated-rules", response_model=list[PersistedActivatedRuleOut])
def list_activated_rules(
    result_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return _service(db).list_activated_rules(result_id)

