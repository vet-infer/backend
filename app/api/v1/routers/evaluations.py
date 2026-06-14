from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.user import User
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.result_repository import ResultRepository
from app.schemas.evaluation import EvaluationCreate, EvaluationOut
from app.schemas.inference import (
    PersistedInferenceResultOut,
    SpanishInferenceResponse,
    SpanishInferenceResult,
)
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


@router.post("/evaluaciones/{evaluation_id}/procesar", response_model=SpanishInferenceResponse)
def procesar_evaluacion_bayes(
    evaluation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario")),
):
    service = InferenceService(
        RuleRepository(db),
        PatientRepository(db),
        EvaluationRepository(db),
        ResultRepository(db),
    )

    persisted_results = service.run_and_persist(evaluation_id)

    resultados_es = []
    for r in persisted_results:
        # Extract activated rules codes
        reglas_codigos = [act_rule.rule.code for act_rule in r.activated_rules if act_rule.rule]

        resultados_es.append(
            SpanishInferenceResult(
                enfermedad=r.disease.name,
                probabilidad=r.probability,
                nivel_riesgo=r.risk_level,
                resultado_sugerido=r.suggested_diagnosis,
                reglas_activadas=reglas_codigos,
                explicacion=r.explanation,
            )
        )

    return SpanishInferenceResponse(
        evaluacion_id=evaluation_id,
        metodo_inferencia="reglas_bayes",
        resultados=resultados_es,
    )
