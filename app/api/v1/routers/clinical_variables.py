from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PermissionPolicy, require_policy
from app.models.user import User
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.disease import ClinicalVariableOut
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/clinical-variables", tags=["Variables clinicas"])


@router.get("", response_model=list[ClinicalVariableOut])
def list_clinical_variables(
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return CatalogService(CatalogRepository(db)).list_clinical_variables()

