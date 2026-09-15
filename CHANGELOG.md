# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Este proyecto no sigue un esquema de versionado formal todavía (API en `1.0.0`); las entradas se agrupan por fecha y, cuando aplica, por el change de OpenSpec que las originó (`openspec/changes/archive/`).

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
