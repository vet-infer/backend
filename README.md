# Backend OE3 - Motor de Inferencia Veterinario

API REST desarrollada con FastAPI para el OE3 de la tesis: aplicacion web con motor de inferencia basado en reglas y Bayes para apoyo a la evaluacion clinica veterinaria en perros y gatos.

El backend gestiona autenticacion, catalogos clinicos, propietarios, pacientes, evaluaciones con facts, procesamiento de inferencia, resultados persistidos, reglas activadas e historial clinico del paciente.

## Stack Tecnologico

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- JWT con `python-jose`
- Docker Compose
- Pytest

## Estructura Principal

```text
Backend-Tesis/
  app/
    api/v1/routers/        # Endpoints REST
    core/                  # Configuracion, seguridad, permisos y DB
    inference/             # Motor de reglas y evaluadores
    models/                # Modelos SQLAlchemy
    repositories/          # Acceso a datos
    schemas/               # Schemas Pydantic
    services/              # Logica de aplicacion
  alembic/                 # Migraciones
  docs/                    # Evidencia y documentacion academica
  tests/                   # Pruebas unitarias/e2e
```

## Variables de Entorno

Crear `.env` a partir de `.env.example`:

```bash
cp .env.example .env
```

Variables relevantes:

```env
APP_NAME=Motor de Inferencia Veterinario
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://vet_app:<POSTGRES_PASSWORD>@postgres:5432/vet_inference
JWT_SECRET=<JWT_SECRET_SEGURO>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
BOOTSTRAP_ADMIN_EMAIL=<ADMIN_EMAIL_LOCAL_OPCIONAL>
BOOTSTRAP_ADMIN_PASSWORD=<ADMIN_PASSWORD_LOCAL_OPCIONAL>
```

Para produccion, cambiar obligatoriamente `JWT_SECRET` y las credenciales bootstrap.

## Ejecucion con Docker

```bash
docker compose up --build
```

Servicios:

- API: `http://localhost:8000`
- Swagger/OpenAPI: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5433`
- pgAdmin: `http://localhost:5050`

Credenciales iniciales de desarrollo:

```text
email: <ADMIN_EMAIL_LOCAL>
password: <ADMIN_PASSWORD_LOCAL>
```

## Ejecucion Local sin Docker

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

La aplicacion tambien inicializa datos de referencia academicos al arrancar, incluyendo roles, especies, razas, sintomas, variables clinicas, enfermedades, niveles de riesgo y reglas base.

## Migraciones

Crear una migracion:

```bash
alembic revision --autogenerate -m "descripcion"
```

Aplicar migraciones:

```bash
alembic upgrade head
```

## Endpoints Principales

### Autenticacion

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### Catalogos Clinicos

- `GET /api/v1/species`
- `GET /api/v1/breeds?species_id={species_id}`
- `GET /api/v1/symptoms`
- `GET /api/v1/clinical-variables`
- `GET /api/v1/diseases`
- `GET /api/v1/risk-levels`

### Propietarios

- `POST /api/v1/owners/`
- `GET /api/v1/owners/`
- `GET /api/v1/owners/{owner_id}`
- `PUT /api/v1/owners/{owner_id}`
- `DELETE /api/v1/owners/{owner_id}`

### Pacientes

- `GET /api/v1/patients`
- `POST /api/v1/patients`
- `GET /api/v1/patients/{patient_id}`
- `PUT /api/v1/patients/{patient_id}`
- `GET /api/v1/patients/{patient_id}/history`

### Evaluaciones e Inferencia

- `POST /api/v1/evaluations`
- `GET /api/v1/evaluations/{evaluation_id}`
- `GET /api/v1/patients/{patient_id}/evaluations`
- `POST /api/v1/evaluaciones/{evaluation_id}/procesar`
- `GET /api/v1/evaluations/{evaluation_id}/results`
- `GET /api/v1/results/{result_id}/activated-rules`

## Flujo Clinico OE3

1. Login y obtencion de JWT.
2. Consulta de catalogos clinicos normalizados.
3. Registro o seleccion de propietario.
4. Registro de paciente con `owner_id`, `species_id` y `breed_id`.
5. Creacion de evaluacion clinica con facts:

```json
{
  "patient_id": 1,
  "reason": "Poliuria y polidipsia",
  "observations": "Paciente con perdida de peso",
  "facts": [
    { "fact_key": "poliuria", "value": true, "source_type": "symptom" },
    { "fact_key": "polidipsia", "value": true, "source_type": "symptom" },
    { "fact_key": "glucosa", "value": 280, "source_type": "clinical_variable" },
    { "fact_key": "glucosuria", "value": "presente", "source_type": "clinical_variable" }
  ]
}
```

6. Procesamiento mediante motor hibrido reglas + Bayes.
7. Consulta de resultados, reglas activadas e historial clinico.

## Pruebas

Ejecutar suite de pruebas:

```bash
pytest
```

Pruebas/evidencia disponibles:

- `tests/e2e_backend_flow.py`
- `tests/run_clinical_validation.py`
- `clinical_validation_report.json`
- `docs/paso6_flujo_e2e_backend.md`

## Consideraciones de Seguridad

- Los endpoints clinicos protegidos requieren JWT.
- El `apiClient` frontend debe enviar `Authorization: Bearer <token>`.
- En produccion, no usar credenciales bootstrap por defecto.
- Ajustar `CORS_ORIGINS` al dominio real del frontend.

## Estado Academico

Este backend cubre el flujo end-to-end del OE3: autenticacion, datos maestros clinicos, registro de pacientes, evaluaciones con facts, inferencia hibrida, resultados persistidos, reglas activadas e historial clinico trazable por paciente.

