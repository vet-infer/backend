from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.user import User
from app.repositories.species_repository import SpeciesRepository
from app.schemas.species import SpeciesCreate, SpeciesOut, SpeciesUpdate
from app.services.species_service import SpeciesService

router = APIRouter(prefix="/species", tags=["Especies"])


@router.get("", response_model=list[SpeciesOut])
def list_species(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    return SpeciesService(SpeciesRepository(db)).list_species(skip=skip, limit=limit)


@router.get("/{species_id}", response_model=SpeciesOut)
def get_species(
    species_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    return SpeciesService(SpeciesRepository(db)).get_species(species_id)


@router.post("", response_model=SpeciesOut, status_code=status.HTTP_201_CREATED)
def create_species(
    payload: SpeciesCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario")),
):
    return SpeciesService(SpeciesRepository(db)).create_species(payload)


@router.put("/{species_id}", response_model=SpeciesOut)
def update_species(
    species_id: int,
    payload: SpeciesUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario")),
):
    return SpeciesService(SpeciesRepository(db)).update_species(species_id, payload)


@router.delete("/{species_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_species(
    species_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario")),
):
    SpeciesService(SpeciesRepository(db)).delete_species(species_id)
