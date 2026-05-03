from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import (
    auth,
    clinical_variables,
    diseases,
    evaluations,
    history,
    inference,
    patients,
    results,
    rules,
    symptoms,
    users,
)
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.exceptions import register_exception_handlers
from app.models import *  # noqa: F403
from app.services.bootstrap_service import bootstrap_reference_data


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
app.include_router(patients.router, prefix=settings.api_v1_prefix)
app.include_router(evaluations.router, prefix=settings.api_v1_prefix)
app.include_router(diseases.router, prefix=settings.api_v1_prefix)
app.include_router(symptoms.router, prefix=settings.api_v1_prefix)
app.include_router(clinical_variables.router, prefix=settings.api_v1_prefix)
app.include_router(rules.router, prefix=settings.api_v1_prefix)
app.include_router(inference.router, prefix=settings.api_v1_prefix)
app.include_router(results.router, prefix=settings.api_v1_prefix)
app.include_router(history.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok"}
