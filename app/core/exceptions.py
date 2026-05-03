from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Error de aplicación"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Recurso no encontrado"


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "No autorizado"


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Permisos insuficientes"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Conflicto con el estado actual del recurso"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
