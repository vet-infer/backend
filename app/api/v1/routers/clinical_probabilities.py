from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import PermissionPolicy, require_policy
from app.models.user import User
from app.repositories.clinical_probability_repository import ClinicalProbabilityRepository
from app.schemas.clinical_probability import (
    ClinicalProbabilityCreate,
    ClinicalProbabilityOut,
    ClinicalProbabilityUpdate,
)
from app.services.clinical_probability_service import ClinicalProbabilityService

router = APIRouter(prefix="/probabilidades-clinicas", tags=["Probabilidades Clinicas"])


def _service(db: Session) -> ClinicalProbabilityService:
    return ClinicalProbabilityService(ClinicalProbabilityRepository(db))


@router.post(
    "",
    response_model=ClinicalProbabilityOut,
    status_code=status.HTTP_201_CREATED,
)
def create_clinical_probability(
    payload: ClinicalProbabilityCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    return _service(db).create_probability(payload.model_dump())


@router.get("", response_model=list[ClinicalProbabilityOut])
def list_clinical_probabilities(
    disease_id: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return _service(db).list_probabilities(disease_id, skip=skip, limit=limit)


@router.get("/{probability_id}", response_model=ClinicalProbabilityOut)
def get_clinical_probability(
    probability_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return _service(db).get_probability(probability_id)


@router.put("/{probability_id}", response_model=ClinicalProbabilityOut)
def update_clinical_probability(
    probability_id: int,
    payload: ClinicalProbabilityUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    updates = payload.model_dump(exclude_unset=True)
    return _service(db).update_probability(probability_id, updates)


@router.delete("/{probability_id}", response_model=ClinicalProbabilityOut)
def delete_clinical_probability(
    probability_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    return _service(db).delete_probability(probability_id)
