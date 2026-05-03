from collections.abc import Callable

from fastapi import Depends

from app.core.exceptions import ForbiddenError
from app.core.security import get_current_user
from app.models.user import User


def require_roles(*roles: str) -> Callable:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        role_name = current_user.role.name if current_user.role else None
        if role_name not in roles:
            raise ForbiddenError("El usuario no tiene permisos para esta operación")
        return current_user

    return dependency
