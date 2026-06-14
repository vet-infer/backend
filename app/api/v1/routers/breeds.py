from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import PermissionPolicy, require_policy
from app.models.user import User
from app.repositories.breed_repository import BreedRepository
from app.schemas.breed import BreedCreate, BreedOut, BreedUpdate
from app.services.breed_service import BreedService

router = APIRouter(prefix="/breeds", tags=["Razas"])


@router.get("", response_model=list[BreedOut])
def list_breeds(
    species_id: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return BreedService(BreedRepository(db)).list_breeds(species_id=species_id, skip=skip, limit=limit)


@router.get("/{breed_id}", response_model=BreedOut)
def get_breed(
    breed_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return BreedService(BreedRepository(db)).get_breed(breed_id)


@router.post("", response_model=BreedOut, status_code=status.HTTP_201_CREATED)
def create_breed(
    payload: BreedCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    return BreedService(BreedRepository(db)).create_breed(payload)


@router.put("/{breed_id}", response_model=BreedOut)
def update_breed(
    breed_id: int,
    payload: BreedUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    return BreedService(BreedRepository(db)).update_breed(breed_id, payload)


@router.delete("/{breed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_breed(
    breed_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_WRITE)),
):
    BreedService(BreedRepository(db)).delete_breed(breed_id)



