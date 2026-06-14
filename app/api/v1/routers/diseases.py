from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PermissionPolicy, require_policy
from app.models.user import User
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.disease import DiseaseCreate, DiseaseOut
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/diseases", tags=["Enfermedades"])


@router.get("", response_model=list[DiseaseOut])
def list_diseases(
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return CatalogService(CatalogRepository(db)).list_diseases()


@router.post("", response_model=DiseaseOut, status_code=201)
def create_disease(
    payload: DiseaseCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.ADMIN_ONLY)),
):
    return CatalogService(CatalogRepository(db)).create_disease(payload)

