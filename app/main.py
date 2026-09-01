import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.routers import (
    auth,
    clinical_variables,
    clinical_probabilities,
    diseases,
    evaluations,
    history,
    inference,
    owners,
    patients,
    results,
    risk_levels,
    rules,
    symptoms,
    users,
    species,
    breeds,
)
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine, get_db
from app.core.exceptions import register_exception_handlers
from app.models import *  # noqa: F403
from app.services.bootstrap_service import bootstrap_reference_data

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if settings.environment.lower() in {"development", "testing"} else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_reference_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "API REST para evaluacion clinica veterinaria inicial mediante "
        "motor de inferencia basado en reglas IF-THEN."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(users.router, prefix=settings.api_v1_prefix)
app.include_router(owners.router, prefix=settings.api_v1_prefix)
app.include_router(patients.router, prefix=settings.api_v1_prefix)
app.include_router(species.router, prefix=settings.api_v1_prefix)
app.include_router(breeds.router, prefix=settings.api_v1_prefix)
app.include_router(evaluations.router, prefix=settings.api_v1_prefix)
app.include_router(diseases.router, prefix=settings.api_v1_prefix)
app.include_router(symptoms.router, prefix=settings.api_v1_prefix)
app.include_router(clinical_variables.router, prefix=settings.api_v1_prefix)
app.include_router(clinical_probabilities.router, prefix=settings.api_v1_prefix)
app.include_router(risk_levels.router, prefix=settings.api_v1_prefix)
app.include_router(rules.router, prefix=settings.api_v1_prefix)
app.include_router(inference.router, prefix=settings.api_v1_prefix)
app.include_router(results.router, prefix=settings.api_v1_prefix)
app.include_router(history.router, prefix=settings.api_v1_prefix)



@app.get("/health", tags=["Sistema"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check fallo: base de datos no responde")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": "Base de datos no disponible"},
        )
    return {"status": "ok"}
