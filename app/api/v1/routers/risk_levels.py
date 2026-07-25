from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PermissionPolicy, require_policy
from app.models.user import User
from app.repositories.risk_level_repository import RiskLevelRepository
from app.schemas.risk_level import RiskLevelOut
from app.services.risk_level_service import RiskLevelService

router = APIRouter(prefix="/risk-levels", tags=["Niveles de riesgo"])


@router.get("", response_model=list[RiskLevelOut])
def list_risk_levels(
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return RiskLevelService(RiskLevelRepository(db)).list_risk_levels()
