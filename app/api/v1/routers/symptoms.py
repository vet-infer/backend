from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.user import User
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.disease import CatalogItemOut
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/symptoms", tags=["Sintomas"])


@router.get("", response_model=list[CatalogItemOut])
def list_symptoms(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    return CatalogService(CatalogRepository(db)).list_symptoms()
