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
    facts = {fact.fact_key: fact.value for fact in payload.facts}
    return _service(db).run_from_payload(payload.patient_id, facts)


@router.get("/results/{result_id}/activated-rules", response_model=list[PersistedActivatedRuleOut])
def list_activated_rules(
    result_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return _service(db).list_activated_rules(result_id)

