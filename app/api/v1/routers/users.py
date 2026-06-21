from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import PermissionPolicy, require_policy
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.ADMIN_ONLY)),
):
    return UserService(UserRepository(db)).list_users()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_policy(PermissionPolicy.ADMIN_ONLY)),
):
    return UserService(UserRepository(db)).create_user(payload)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_policy(PermissionPolicy.ADMIN_ONLY)),
):
    return UserService(UserRepository(db)).update_user(user_id, payload, current_user_id=current_user.id)


@router.patch("/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_policy(PermissionPolicy.ADMIN_ONLY)),
):
    return UserService(UserRepository(db)).update_user(user_id, UserUpdate(is_active=payload.is_active), current_user_id=current_user.id)

