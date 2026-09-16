# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Este proyecto no sigue un esquema de versionado formal todavía (API en `1.0.0`); las entradas se agrupan por fecha y, cuando aplica, por el change de OpenSpec que las originó (`openspec/changes/archive/`).

## [2026-09-03] — Endurecimiento del motor de inferencia (Fase 4)

Change de OpenSpec: [`archive/2026-09-03-harden-inference-engine-phase4`](../openspec/changes/archive/2026-09-03-harden-inference-engine-phase4/). Specs modificadas: [`inference-engine`](../openspec/specs/inference-engine/spec.md), [`auth`](../openspec/specs/auth/spec.md) (nueva).

### Added

- Rate limiting por IP en `POST /api/v1/auth/login` (por defecto `10/minute`), para mitigar fuerza bruta de credenciales: un intento que excede el límite responde `429` sin llegar a verificar la contraseña contra la base de datos.
- Rate limiting por IP en los endpoints que ejecutan el motor de inferencia o el simulador de reglas (por defecto `30/minute`): `POST /inference/run`, `POST /inference/evaluations/{evaluation_id}/run`, `POST /evaluaciones/{evaluation_id}/procesar`, `POST /rules/simulate`.
- `app/core/rate_limit.py`: instancia única de `slowapi.Limiter` (`get_remote_address` como identificador de cliente, backend de conteo en memoria del proceso), registrada en `app.state.limiter`.
- Exception handler de `RateLimitExceeded` en `app/core/exceptions.py`, devolviendo `429 {"detail": "..."}` con el mismo shape que el resto de errores manejados de la API.
- Settings nuevos en `app/core/config.py`: `rate_limit_enabled` (default `True`), `rate_limit_login`, `rate_limit_inference`. `tests/conftest.py` fuerza `RATE_LIMIT_ENABLED=false` por defecto para toda la suite (el limiter es un singleton de proceso compartido entre tests, igual que el cache de Fase 3); los tests dedicados de esta fase (`tests/test_rate_limiting.py`) lo habilitan explícitamente y resetean su storage antes/después de cada uno.
- Nueva dependencia: `slowapi==0.1.10`.
- Nuevos tests: `tests/test_rate_limiting.py` (7 tests: shape del 429, login bloquea sin verificar contraseña tras el límite, login dentro del límite no se bloquea, cada uno de los 4 endpoints de inferencia/simulación bloquea tras su límite, rutas no cubiertas por esta fase no se ven afectadas), más 2 tests de configuración en `tests/test_config.py`.

### Known issues (no resueltos en este cambio)

- El rate limiting es en memoria del proceso, no compartido entre réplicas; si el despliegue pasa a múltiples instancias del backend, requiere migrar el storage de `slowapi` a un backend compartido (Redis). Documentado como Non-Goal explícito en el diseño de esta fase.
- La identificación del cliente es por IP directa (`get_remote_address`); si se despliega detrás de un proxy/load balancer, debe revisarse el manejo de `X-Forwarded-For`.

---

**Tests:** 122/122 pasan (`pytest`, backend; 115 previos + 7 nuevos; 2 fallos preexistentes y no relacionados a este cambio, por configuración local de `.env`, quedan fuera de este conteo). **Archivos nuevos:** `app/core/rate_limit.py`, `tests/test_rate_limiting.py`. **Archivos modificados:** `requirements.txt`, `.env.example`, `app/core/config.py`, `app/core/exceptions.py`, `app/main.py`, `app/api/v1/routers/auth.py`, `app/api/v1/routers/inference.py`, `app/api/v1/routers/evaluations.py`, `app/api/v1/routers/rules.py`, `tests/conftest.py`, `tests/test_config.py`.

## [2026-09-01] — Endurecimiento del motor de inferencia (Fase 3)

Change de OpenSpec: [`archive/2026-09-01-harden-inference-engine-phase3`](../openspec/changes/archive/2026-09-01-harden-inference-engine-phase3/). Spec modificada: [`inference-engine`](../openspec/specs/inference-engine/spec.md).

### Added

- Endpoint de simulación de reglas: `POST /api/v1/rules/simulate` evalúa un conjunto de condiciones contra facts de ejemplo sin requerir que exista una regla real y sin persistir nada. Reutiliza `InferenceEngine.evaluate` (mismo motor que una inferencia real) con un objeto de regla efímero, no una lógica de matching paralela. Requiere `ADMIN_ONLY`, igual que el resto de `/rules`.
- Cache en memoria de reglas activas por especie, catálogo de enfermedades activas y probabilidades clínicas activas (`app/core/cache.py`), invalidado explícitamente (`invalidate_all()`) en cada escritura de reglas o probabilidades clínicas — sin TTL, para no arriesgar servir datos desactivados/desactualizados. El cache guarda snapshots inmutables (`RuleView`/`ConditionView`/`DiseaseView` en `app/inference/rule_view.py`; `DiseaseSnapshot`/`ClinicalProbabilitySnapshot` en `app/repositories/snapshots.py`), no objetos ORM de SQLAlchemy — cachear objetos ORM directamente produce `DetachedInstanceError` en cuanto una request con una sesión distinta accede a sus atributos tras el primer `commit()` en cualquier sesión; se confirmó reproduciéndolo en la suite de tests real antes de corregirlo.
- Cobertura de tests nueva: `tests/test_condition_evaluator.py` (33 tests unitarios de los 9 operadores de `ConditionEvaluator`, incluyendo límites exactos), `tests/test_bayes.py` (normalización con `likelihood` total 0 o negativo), `tests/test_authorization_negative.py` (8 tests de 403 para `/rules` y `/inference` con roles sin permiso — antes no existía un solo test de autorización negativa en todo el repositorio), `tests/test_rule_simulation.py`, `tests/test_inference_cache.py`.
- Fixture `autouse` en `tests/conftest.py` que resetea el cache de inferencia antes y después de cada test — el cache es un singleton de proceso (correcto para producción), pero sin resetearlo se filtraba entre tests con bases de datos SQLite aisladas distintas; se detectó y corrigió durante la implementación de esta fase, no era hipotético.

### Changed

- `CatalogRepository.list_diseases`, `RuleRepository.get_active_rules_by_species` y `ClinicalProbabilityRepository.list_active_by_disease_ids` (nuevo método, reemplaza una consulta inline en `InferenceService` que bypaseaba el repositorio) ahora pasan por el cache antes de consultar la base de datos.

---

**Tests:** 115/115 pasan (`pytest`, backend; 69 previos + 46 nuevos). **Archivos nuevos:** `app/core/cache.py`, `app/inference/rule_view.py`, `app/repositories/snapshots.py`, `tests/test_condition_evaluator.py`, `tests/test_authorization_negative.py`, `tests/test_rule_simulation.py`, `tests/test_inference_cache.py`. **Archivos modificados:** `app/schemas/rule.py`, `app/services/rule_service.py`, `app/api/v1/routers/rules.py`, `app/repositories/rule_repository.py`, `app/repositories/catalog_repository.py`, `app/repositories/clinical_probability_repository.py`, `app/services/inference_service.py`, `tests/conftest.py`, `tests/test_bayes.py`, `tests/test_exception_handling.py`.

## [2026-09-01] — Endurecimiento del motor de inferencia (Fase 2)

Change de OpenSpec: [`archive/2026-09-01-harden-inference-engine-phase2`](../openspec/changes/archive/2026-09-01-harden-inference-engine-phase2/). Spec modificada: [`inference-engine`](../openspec/specs/inference-engine/spec.md).

### Added

- Versionado no destructivo de resultados de inferencia: `InferenceResult` gana `is_current` (default `True`) y `superseded_at`. Al volver a ejecutar la inferencia sobre una evaluación clínica que ya tiene resultados, los anteriores se marcan `is_current=False, superseded_at=<ahora>` en la misma transacción, en vez de mezclarse con los nuevos o perderse. Migración de Alembic: `c1a9e5f0b736_add_is_current_to_inference_results.py`.
- `ResultRepository.list_by_evaluation` / `InferenceService.list_results` / `GET /api/v1/evaluations/{evaluation_id}/results` aceptan `include_history` (default `False`): por defecto devuelven solo los resultados vigentes; con `include_history=true` devuelven también las ejecuciones anteriores marcadas como superadas.
- `GET /health` ahora ejecuta `SELECT 1` contra la base de datos configurada; responde `503 {"status": "error", ...}` si la base de datos no está disponible, en vez de reportar siempre `{"status": "ok"}` sin verificar nada.
- Nuevos tests: `tests/test_result_versioning.py`, `tests/test_deprecated_inference_endpoint.py`, `tests/test_health_check.py`.

### Changed

- `CatalogRepository.list_diseases` acepta `species_id` opcional y filtra en SQL (antes se traían todas las enfermedades activas de todas las especies y se filtraba en Python dentro de `InferenceService._run_hybrid_inference`). La consulta de `ClinicalProbability` en el mismo método ahora filtra por `disease_id.in_(...)` en vez de traer todas las activas. Sin cambio de comportamiento observable — mismo resultado, menos filas leídas.
- `POST /inference/evaluations/{evaluation_id}/run` queda marcado `deprecated=True` en OpenAPI, con la documentación señalando `POST /evaluaciones/{id}/procesar` como endpoint canónico (confirmado que es el único que usa el frontend). No cambia su comportamiento funcional; `POST /inference/run` (previsualización sin persistir) no se toca — no es un duplicado.

### Known issues (no resueltos en este cambio)

- La migración `c1a9e5f0b736` no se pudo verificar contra PostgreSQL real en este entorno (Docker Desktop no estaba disponible). Se verificó por coincidencia exacta de patrón con una migración equivalente ya probada en producción (`a6dc8e396b9c`) y por integridad de la cadena de Alembic (`alembic heads` resuelve a un único head). Pendiente: correr `alembic upgrade head` contra Postgres real la próxima vez que Docker esté disponible.

---

**Tests:** 65/65 pasan (`pytest`, backend; 59 de Fase 1 + 6 nuevos). **Archivos modificados:** `app/models/inference_result.py`, `app/repositories/result_repository.py`, `app/repositories/catalog_repository.py`, `app/services/inference_service.py`, `app/api/v1/routers/inference.py`, `app/api/v1/routers/evaluations.py`, `app/main.py`. **Archivos nuevos:** `alembic/versions/c1a9e5f0b736_add_is_current_to_inference_results.py`, `tests/test_result_versioning.py`, `tests/test_deprecated_inference_endpoint.py`, `tests/test_health_check.py`.

## [2026-09-01] — Endurecimiento del motor de inferencia (Fase 1)

Change de OpenSpec: [`archive/2026-09-01-harden-inference-engine-phase1`](../openspec/changes/archive/2026-09-01-harden-inference-engine-phase1/). Spec resultante: [`inference-engine`](../openspec/specs/inference-engine/spec.md).

### Added

- Validación de reglas: `RuleConditionCreate.operator` (`app/schemas/rule.py`) ahora es un `Literal` restringido a los 9 operadores soportados por el motor (`eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `between`, `contains`, `in`); crear o actualizar una regla con un operador fuera de ese conjunto responde 422 en vez de aceptarse en silencio.
- Validación de forma de `expected_value` según el operador (nuevo `model_validator` en el mismo schema): los operadores numéricos exigen un valor convertible a `float`; `between` exige `[min, max]` o `{"min": x, "max": y}` con `min <= max`; `in` exige lista o string. Aplica también a `RuleUpdate.conditions`.
- Logging estructurado del motor de inferencia:
  - `app/main.py` configura `logging.basicConfig` al arranque (DEBUG en `development`/`testing`, INFO en el resto) si no hay configuración previa.
  - `InferenceEngine.evaluate` (`app/inference/engine.py`) acepta `evaluation_id`/`patient_id` opcionales y registra en DEBUG cada regla evaluada (activada o rechazada) con esa correlación.
  - `ConditionEvaluator.matches` (`app/inference/evaluator.py`) registra en WARNING cuando el valor observado no es convertible al tipo esperado por el operador, y continúa evaluando el resto de las condiciones/reglas en vez de fallar.
  - `BayesService.calcular_probabilidad_bayes` (`app/services/bayes_service.py`) registra en DEBUG la verosimilitud calculada por enfermedad y en WARNING cuando no hay `ClinicalProbability` coincidente para una evidencia.
- Manejador de excepciones genérico (`app/core/exceptions.py`): un `@app.exception_handler(Exception)` captura cualquier error no controlado durante una request, lo registra completo en el log del servidor (`logger.exception`) y responde `500 {"detail": "Error interno del servidor"}` sin exponer traza de Python ni rutas internas. No intercepta `AppException` ni `RequestValidationError`, que conservan su comportamiento.
- Nuevos tests: `tests/test_rule_validation.py` (25 casos de validación de reglas), `tests/test_exception_handling.py` (manejo de errores no controlados vs. errores ya manejados), más casos de logging en `tests/test_inference_engine.py` y `tests/test_bayes.py`.

### Changed

- `BayesService.calcular_probabilidad_bayes` ahora usa la **razón de verosimilitud** `probability_given_disease / general_probability` (en vez de `probability_given_disease` en crudo) cuando existe una `ClinicalProbability` coincidente para la evidencia. Esto corrige que evidencia poco discriminante entre enfermedades (p. ej. síntomas presentes en varias enfermedades candidatas) inflara la probabilidad normalizada de enfermedades sin evidencia específica. `general_probability` estaba sembrado y validado desde antes pero no se usaba en el cálculo. Si `general_probability` es 0 o inválido se aplica un piso (`1e-6`) con warning; el comportamiento de `bayes_smoothing_factor` para evidencia sin `ClinicalProbability` coincidente no cambia.
  - **Impacto observable:** cambian los valores de `probability` devueltos por `/inference/run`, `/inference/evaluations/{id}/run` y `/evaluaciones/{id}/procesar`; `risk_level` puede cambiar de clasificación en casos con evidencia poco discriminante. No cambia el shape del contrato de ninguna API.
- Corrección de dato semilla (`app/seeds/clinical_reference_data.json`): `ClinicalProbability` de `glucosuria` para Diabetes mellitus (Perro y Gato) usaba `expected_value: "presente"`, mientras que las reglas `DM-R03`/`DM-R04`/`DM-CAT-R03`/`DM-CAT-R04` esperaban `"positiva"` — inconsistencia que impedía que esas reglas se activaran nunca. Se alineó a `"positiva"` (consistente con `allowed_values` de la variable en `FactDefinition`).

### Removed

- `app/inference/risk.py` (`risk_from_score`): el motor de reglas calculaba un `risk_level` a partir del `score` ponderado de reglas activadas, pero ese valor nunca se consumía — el `risk_level` final del resultado híbrido siempre lo determina `BayesService.determinar_nivel_riesgo` sobre la probabilidad bayesiana. Se eliminó el cálculo huérfano; `InferenceEngine.evaluate` sigue calculando y exponiendo `score`, pero ya no agrega `risk_level` al resultado.
- Settings `inference_high_score_threshold` / `inference_moderate_score_threshold` (`app/core/config.py`): sin consumidores tras retirar `risk_from_score`.

### Fixed

- Dos tests que fallaban en la rama base antes de este cambio (`test_hybrid_inference_flow_and_risk_assignment`, `test_spanish_inference_endpoint`) ahora pasan: la causa combinaba la corrección de verosimilitud bayesiana descrita arriba y la inconsistencia de dato semilla de `glucosuria`.

### Known issues (no resueltos en este cambio)

- `backend/tests/run_clinical_validation.py` (y el reporte `backend/clinical_validation_report.json` que genera) no pudieron ejecutarse: el script usa la base de datos local persistente `oe3_runtime.db`, cuyo esquema está desactualizado respecto a las migraciones de Alembic. Además, las migraciones del proyecto usan sintaxis específica de PostgreSQL (`ALTER COLUMN ... SET NOT NULL`) incompatible con SQLite, por lo que ese archivo local no tiene un camino de migración válido tal como están escritas hoy. Fuera del alcance de este cambio — usar PostgreSQL vía `docker-compose up` para validación real.

---

**Tests:** 59/59 pasan (`pytest`, backend). **Archivos modificados:** `app/schemas/rule.py`, `app/main.py`, `app/inference/engine.py`, `app/inference/evaluator.py`, `app/services/bayes_service.py`, `app/core/exceptions.py`, `app/core/config.py`, `app/seeds/clinical_reference_data.json`, `tests/test_inference_engine.py`, `tests/test_bayes.py`. **Archivos nuevos:** `tests/test_rule_validation.py`, `tests/test_exception_handling.py`. **Archivos eliminados:** `app/inference/risk.py`.
