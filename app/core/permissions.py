from collections.abc import Callable

from fastapi import Depends

from app.core.exceptions import ForbiddenError
from app.core.security import get_current_user
from app.models.user import User


class PermissionPolicy:
    ADMIN_ONLY = "admin_only"
    CLINICAL_READ = "clinical_read"
    CLINICAL_WRITE = "clinical_write"


def require_roles(*roles: str) -> Callable:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        role_name = current_user.role.name if current_user.role else None
        if role_name not in roles:
            raise ForbiddenError("El usuario no tiene permisos para esta operación")
        return current_user

    return dependency


def require_policy(policy: str) -> Callable:
    from app.core.constants import ADMIN_ROLES, READ_ROLES, WRITE_ROLES

    policies = {
        PermissionPolicy.ADMIN_ONLY: ADMIN_ROLES,
        PermissionPolicy.CLINICAL_READ: READ_ROLES,
        PermissionPolicy.CLINICAL_WRITE: WRITE_ROLES,
    }
    return require_roles(*policies[policy])
