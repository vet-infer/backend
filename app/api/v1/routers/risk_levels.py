from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.risk_level import RiskLevel
from app.models.user import User
from app.schemas.risk_level import RiskLevelOut

router = APIRouter(prefix="/risk-levels", tags=["Niveles de riesgo"])


@router.get("", response_model=list[RiskLevelOut])
def list_risk_levels(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "veterinario", "evaluador")),
):
    return (
        db.query(RiskLevel)
        .filter(RiskLevel.is_active.is_(True))
        .order_by(RiskLevel.sort_order)
        .all()
    )
