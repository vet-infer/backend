from fastapi import APIRouter, Depends, Query, HTTPException, status
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

router = APIRouter(prefix="/probabilidades-clinicas", tags=["Probabilidades Clinicas"])


def _repository(db: Session) -> ClinicalProbabilityRepository:
    return ClinicalProbabilityRepository(db)


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
    repo = _repository(db)
    return repo.crear_probabilidad(payload.model_dump())


@router.get("", response_model=list[ClinicalProbabilityOut])
def list_clinical_probabilities(
    disease_id: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    repo = _repository(db)
    if disease_id is not None:
        return repo.listar_probabilidades_por_enfermedad(disease_id)
    return repo.listar_probabilidades(skip=skip, limit=limit)


@router.get("/{probability_id}", response_model=ClinicalProbabilityOut)
def get_clinical_probability(
    probability_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    repo = _repository(db)
    prob = repo.obtener_probabilidad_por_id(probability_id)
    if prob is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Probabilidad clinica no encontrada",
        )
    return prob


@router.put("/{probability_id}", response_model=ClinicalProbabilityOut)
def update_clinical_probability(
    probability_id: int,
    payload: ClinicalProbabilityUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    repo = _repository(db)
    # Filter out unset/None fields to avoid overwriting unless intended
    updates = payload.model_dump(exclude_unset=True)
    prob = repo.actualizar_probabilidad(probability_id, updates)
    if prob is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Probabilidad clinica no encontrada o no se pudo actualizar",
        )
    return prob


@router.delete("/{probability_id}", response_model=ClinicalProbabilityOut)
def delete_clinical_probability(
    probability_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    repo = _repository(db)
    prob = repo.desactivar_probabilidad(probability_id)
    if prob is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Probabilidad clinica no encontrada o no se pudo desactivar",
        )
    return prob



