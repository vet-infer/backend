# Backend FastAPI - Motor de Inferencia Veterinario

API REST academica para registrar pacientes, evaluaciones clinicas y ejecutar un motor de inferencia basado en reglas IF-THEN para apoyar la deteccion temprana de enfermedades degenerativas en perros y gatos.

## Ejecucion local

```bash
cp .env.example .env
docker compose up --build
```

La API queda disponible en `http://localhost:8000` y la documentacion Swagger en `http://localhost:8000/docs`.

Credenciales iniciales de desarrollo:

```text
email: admin@example.com
password: Admin12345
```

## Migraciones

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Durante desarrollo, la aplicacion tambien crea las tablas al iniciar para facilitar la ejecucion academica inicial.

## Flujo principal

1. Iniciar sesion en `/api/v1/auth/login`.
2. Registrar enfermedades degenerativas seleccionadas.
3. Crear reglas IF-THEN con condiciones clinicas.
4. Registrar pacientes y evaluaciones clinicas.
5. Ejecutar `/api/v1/inference/evaluations/{id}/run`.
6. Consultar resultados, reglas activadas e historial clinico.
