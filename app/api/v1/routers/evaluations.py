from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import PermissionPolicy, require_policy
from app.core.rate_limit import limiter
from app.models.user import User
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.result_repository import ResultRepository
from app.schemas.evaluation import EvaluationCreate, EvaluationOut, FactDefinitionOut
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
    current_user: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    return _evaluation_service(db).create_evaluation(payload, current_user.id)


@router.get("/evaluations", response_model=list[EvaluationOut])
def list_evaluations(
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return _evaluation_service(db).list_recent()


@router.get("/evaluation-facts", response_model=list[FactDefinitionOut])
def list_evaluation_fact_definitions(
    species_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    """Metadatos clinicos activos para el formulario, sin exponer la logica de las reglas."""
    return _evaluation_service(db).list_fact_definitions(species_id)


@router.get("/evaluation-symptoms", response_model=list[FactDefinitionOut])
def list_evaluation_symptom_definitions(
    species_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return _evaluation_service(db).list_fact_definitions_by_source("symptom", species_id)


@router.get("/evaluation-clinical-variables", response_model=list[FactDefinitionOut])
def list_evaluation_clinical_variable_definitions(
    species_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return _evaluation_service(db).list_fact_definitions_by_source("clinical_variable", species_id)


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return _evaluation_service(db).get_evaluation(evaluation_id)


@router.get("/patients/{patient_id}/evaluations", response_model=list[EvaluationOut])
def list_patient_evaluations(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return _evaluation_service(db).list_by_patient(patient_id)


@router.get("/evaluations/{evaluation_id}/results", response_model=list[PersistedInferenceResultOut])
def list_evaluation_results(
    evaluation_id: int,
    include_history: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    service = InferenceService(
        RuleRepository(db),
        PatientRepository(db),
        EvaluationRepository(db),
        ResultRepository(db),
    )
    return service.list_results(evaluation_id, include_history=include_history)


@router.post("/evaluaciones/{evaluation_id}/procesar", response_model=SpanishInferenceResponse)
@limiter.limit(settings.rate_limit_inference)
def procesar_evaluacion_bayes(
    request: Request,
    evaluation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
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

