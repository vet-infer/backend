# Despliegue beta en Railway - Backend OE3

## Arquitectura beta

```text
Frontend React/Vite -> Vercel o Railway Static
Backend FastAPI     -> Railway Web Service
Base de datos       -> Railway PostgreSQL
```

## Servicios desplegados

```text
Proyecto Railway: oe3-beta
Backend API:      https://api-production-f723.up.railway.app
Frontend beta:    https://frontend-production-f6f8.up.railway.app
Swagger backend:  https://api-production-f723.up.railway.app/docs
Healthcheck:      https://api-production-f723.up.railway.app/health
```

## Variables requeridas en Railway

```env
APP_NAME=Motor de Inferencia Veterinario
ENVIRONMENT=production
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET=<secreto-seguro-generado-para-beta>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=["https://frontend-production-f6f8.up.railway.app","http://localhost:5173"]
BOOTSTRAP_ADMIN_EMAIL=<correo-admin-beta>
BOOTSTRAP_ADMIN_PASSWORD=<password-admin-beta>
DEFAULT_PAGE_SIZE=50
MAX_PAGE_SIZE=100
BAYES_DEFAULT_PRIOR=0.20
BAYES_SMOOTHING_FACTOR=0.50
PROBABILITY_PRECISION=4
INFERENCE_HIGH_SCORE_THRESHOLD=7.0
INFERENCE_MODERATE_SCORE_THRESHOLD=4.0
SEED_DATA_PATH=app/seeds/clinical_reference_data.json
```

## Comando de arranque

El `Dockerfile` usa:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Railway inyecta `PORT` automaticamente. En local se conserva el puerto 8000.

## Pasos generales

1. Crear un proyecto en Railway.
2. Agregar un servicio PostgreSQL.
3. Desplegar este directorio `Backend-Tesis` como servicio web.
4. Configurar las variables de entorno anteriores.
5. Verificar `https://<backend-railway>/health`.
6. Verificar `https://<backend-railway>/docs`.
7. Configurar `VITE_API_BASE_URL=https://<backend-railway>` en el frontend.
8. Actualizar `CORS_ORIGINS` con el dominio final del frontend.
9. Definir `BOOTSTRAP_ADMIN_EMAIL` y `BOOTSTRAP_ADMIN_PASSWORD`.
10. Redeplegar `api` para crear el administrador inicial.

## Evidencia OE3 sugerida

- Captura de Railway con el servicio backend activo.
- Captura del servicio PostgreSQL asociado.
- Captura de `/health` con respuesta `{"status":"ok"}`.
- Captura de Swagger `/docs`.
- Capturas Network del frontend consumiendo endpoints reales con JWT.
- Payloads de login, catalogos, pacientes, evaluaciones e inferencia.

## Riesgos y controles

- No usar `JWT_SECRET` de desarrollo en beta.
- No exponer `.env` ni credenciales en el repositorio.
- Confirmar que `CORS_ORIGINS` coincida exactamente con el dominio del frontend.
- Hacer respaldo de PostgreSQL antes de pruebas con usuarios reales.
- Mantener Alembic como mecanismo formal de migracion hacia Azure.
