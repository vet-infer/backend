from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PermissionPolicy, require_policy
from app.models.user import User
from app.repositories.rule_repository import RuleRepository
from app.schemas.rule import RuleCreate, RuleOut, RuleUpdate
from app.services.rule_service import RuleService

router = APIRouter(prefix="/rules", tags=["Reglas de inferencia"])


@router.get("", response_model=list[RuleOut])
def list_rules(
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.CLINICAL_READ)),
):
    return RuleService(RuleRepository(db)).list_rules()


@router.post("", response_model=RuleOut, status_code=201)
def create_rule(
    payload: RuleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.ADMIN_ONLY)),
):
    return RuleService(RuleRepository(db)).create_rule(payload)


@router.put("/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.ADMIN_ONLY)),
):
    return RuleService(RuleRepository(db)).update_rule(rule_id, payload)

