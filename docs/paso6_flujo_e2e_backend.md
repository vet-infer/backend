# Paso 6 - Validacion end-to-end del backend API REST

## 1. Diagnostico inicial

El flujo end-to-end se puede ejecutar desde Swagger, Postman o el script automatizado `tests/e2e_backend_flow.py` sin intervencion manual directa en PostgreSQL.

Endpoints confirmados en el codigo:

| Modulo | Endpoint |
| --- | --- |
| Autenticacion | `POST /api/v1/auth/login` |
| Owners / duenos | `POST /api/v1/owners/`, `GET /api/v1/owners/{owner_id}` |
| Species / especies | `GET /api/v1/species` |
| Breeds / razas | `GET /api/v1/breeds?species_id={species_id}` |
| Patients / pacientes | `POST /api/v1/patients`, `GET /api/v1/patients/{patient_id}` |
| Evaluations / evaluaciones | `POST /api/v1/evaluations`, `GET /api/v1/evaluations/{evaluation_id}` |
| Procesamiento de inferencia | `POST /api/v1/evaluaciones/{evaluation_id}/procesar` |
| Resultados | `GET /api/v1/evaluations/{evaluation_id}/results` |
| Reglas activadas | `GET /api/v1/results/{result_id}/activated-rules` |
| Historial clinico | `GET /api/v1/patients/{patient_id}/history` |

No existen endpoints separados para "registrar sintomas" y "registrar variables" despues de creada la evaluacion. El backend registra ambos como `evaluation_facts` dentro del payload de `POST /api/v1/evaluations`.

Riesgo detectado y corregido durante la ejecucion: `POST /api/v1/owners/` devolvia 500 porque `OwnerRepository` no implementaba `create`, `get_by_id`, `update` y `delete` como los invocaba `OwnerService`. Se corrigio el repositorio y el flujo paso correctamente.

## 2. Mapa de endpoints del flujo completo

| Paso | Accion | Metodo | Endpoint | JWT | Payload | Respuesta esperada | Tabla afectada |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Login | POST | `/api/v1/auth/login` | No | email, password | 200 + access_token | users |
| 2 | Obtener especies | GET | `/api/v1/species` | Si | N/A | 200 + lista | species |
| 3 | Obtener razas | GET | `/api/v1/breeds?species_id=1` | Si | N/A | 200 + lista | breeds |
| 4 | Crear dueno | POST | `/api/v1/owners/` | No | OwnerCreate | 201 + owner.id | owners |
| 5 | Consultar dueno | GET | `/api/v1/owners/{owner_id}` | No | N/A | 200 + owner | owners |
| 6 | Crear paciente | POST | `/api/v1/patients` | Si | PatientCreate | 201 + patient.id | patients |
| 7 | Consultar paciente | GET | `/api/v1/patients/{patient_id}` | Si | N/A | 200 + patient | patients |
| 8 | Crear evaluacion con sintomas y variables | POST | `/api/v1/evaluations` | Si | EvaluationCreate con facts | 201 + evaluation.id + facts | evaluations, evaluation_facts, clinical_history |
| 9 | Procesar evaluacion | POST | `/api/v1/evaluaciones/{evaluation_id}/procesar` | Si | N/A | 200 + resultados | inference_results, activated_rules, clinical_history |
| 10 | Consultar resultados | GET | `/api/v1/evaluations/{evaluation_id}/results` | Si | N/A | 200 + resultados persistidos | inference_results |
| 11 | Consultar reglas activadas | GET | `/api/v1/results/{result_id}/activated-rules` | Si | N/A | 200 + reglas | activated_rules |
| 12 | Consultar historial | GET | `/api/v1/patients/{patient_id}/history` | Si | N/A | 200 + eventos | clinical_history |

## 3. Precondiciones

Antes de ejecutar el flujo deben existir:

| Recurso | Estado requerido | Verificacion rapida |
| --- | --- | --- |
| usuario veterinario/admin activo | Requerido | `SELECT email, is_active FROM users;` |
| roles | Requerido | `SELECT * FROM roles;` |
| species | Perro/Gato | `SELECT * FROM species;` |
| breeds | Razas por especie | `SELECT * FROM breeds;` |
| diseases | Diabetes mellitus y otras | `SELECT * FROM diseases;` |
| risk_levels | Bajo, Moderado, Alto | `SELECT * FROM risk_levels;` |
| symptoms | Sintomas clinicos | `SELECT * FROM symptoms;` |
| clinical_variables | glucosa, glucosuria, etc. | `SELECT * FROM clinical_variables;` |
| inference_rules | DM-R03, DM-R04 | `SELECT * FROM inference_rules;` |
| rule_conditions | condiciones de reglas | `SELECT * FROM rule_conditions;` |
| clinical_probabilities | probabilidades Bayes | `SELECT * FROM clinical_probabilities;` |

## 4. Caso clinico recomendado

Caso validado: diabetes mellitus canina de riesgo alto.

| Campo | Valor |
| --- | --- |
| Enfermedad objetivo | Diabetes mellitus |
| Especie | Perro |
| Raza | Poodle |
| Paciente | Canino adulto/geriatrico |
| Sintomas | poliuria, polidipsia, polifagia, perdida de peso |
| Variables | glucosa 280 mg/dL, glucosuria presente |
| Reglas esperadas | DM-R03, DM-R04 |
| Metodo esperado | reglas_bayes |
| Probabilidad obtenida en ejecucion | 0.6965 |
| Nivel esperado/obtenido | Alto |

Nota tecnica: la probabilidad quedo en 0.6965, levemente menor que 0.70, pero el riesgo final es Alto porque el motor hibrido combina Bayes con reglas de severidad alta.

## 5. Payloads JSON

Login:

```json
{
  "email": "admin@example.com",
  "password": "Admin12345"
}
```

Crear owner:

```json
{
  "first_name": "Elena",
  "last_name": "Paso6",
  "phone": "+51999000666",
  "email": "paso6.owner@example.com",
  "address": "Av. Validacion OE3 123"
}
```

Crear patient:

```json
{
  "owner_id": 2,
  "name": "Max Paso6",
  "species_id": 1,
  "breed_id": 2,
  "sex": "Macho",
  "birth_date": "2016-05-20",
  "weight": 18.4
}
```

Crear clinical evaluation con sintomas y variables:

```json
{
  "patient_id": 3,
  "reason": "Poliuria, polidipsia y sospecha de diabetes mellitus",
  "observations": "Caso E2E Paso 6 OE3: paciente canino adulto con signos metabolicos.",
  "facts": [
    {"fact_key": "poliuria", "value": true, "source_type": "symptom"},
    {"fact_key": "polidipsia", "value": true, "source_type": "symptom"},
    {"fact_key": "polifagia", "value": true, "source_type": "symptom"},
    {"fact_key": "perdida de peso", "value": true, "source_type": "symptom"},
    {"fact_key": "glucosa", "value": 280.0, "source_type": "clinical_variable"},
    {"fact_key": "glucosuria", "value": "presente", "source_type": "clinical_variable"}
  ]
}
```

Procesar evaluacion:

```http
POST /api/v1/evaluaciones/{evaluation_id}/procesar
Authorization: Bearer <JWT>
```

Consultar resultado:

```http
GET /api/v1/evaluations/{evaluation_id}/results
Authorization: Bearer <JWT>
```

Consultar reglas activadas:

```http
GET /api/v1/results/{result_id}/activated-rules
Authorization: Bearer <JWT>
```

Consultar historial:

```http
GET /api/v1/patients/{patient_id}/history
Authorization: Bearer <JWT>
```

## 6. Respuestas esperadas

| Request | Codigo | Campos minimos | Exito si |
| --- | --- | --- | --- |
| Login | 200 | access_token, token_type | token no vacio |
| Crear owner | 201 | id, first_name, email | id creado |
| Crear patient | 201 | id, owner, species, breed | owner/species/breed coinciden |
| Crear evaluation | 201 | id, patient_id, facts | facts contiene sintomas y variables |
| Procesar | 200 | resultados, probabilidad, nivel_riesgo, reglas_activadas | Diabetes mellitus aparece con Alto |
| Resultados | 200 | id, disease_id, probability, inference_method, risk_level_id | resultado persistido |
| Reglas activadas | 200 | rule_id, fulfilled_conditions | contiene reglas DM-R03/DM-R04 |
| Historial | 200 | event_type, summary | aparecen clinical_evaluation e inference_result |

## 7. Queries SQL de persistencia

```sql
SELECT * FROM owners WHERE id = :owner_id;

SELECT p.id, p.name, p.owner_id, p.species_id, p.breed_id, s.name AS species, b.name AS breed
FROM patients p
JOIN species s ON s.id = p.species_id
LEFT JOIN breeds b ON b.id = p.breed_id
WHERE p.id = :patient_id;

SELECT * FROM evaluations WHERE id = :evaluation_id;

SELECT fact_key, value, source_type
FROM evaluation_facts
WHERE evaluation_id = :evaluation_id
ORDER BY id;

SELECT ir.id, ir.evaluation_id, d.name AS disease, ir.probability,
       ir.inference_method, ir.risk_level, ir.risk_level_id
FROM inference_results ir
JOIN diseases d ON d.id = ir.disease_id
WHERE ir.evaluation_id = :evaluation_id
ORDER BY ir.probability DESC;

SELECT ar.result_id, r.code, r.name
FROM activated_rules ar
JOIN inference_rules r ON r.id = ar.rule_id
WHERE ar.result_id = :result_id
ORDER BY r.code;

SELECT event_type, summary
FROM clinical_history
WHERE patient_id = :patient_id
ORDER BY id;
```

## 8. Queries de integridad

```sql
SELECT 'patients_no_owner' AS check_name, COUNT(*)
FROM patients p LEFT JOIN owners o ON o.id=p.owner_id
WHERE o.id IS NULL
UNION ALL
SELECT 'patients_no_species', COUNT(*)
FROM patients p LEFT JOIN species s ON s.id=p.species_id
WHERE s.id IS NULL
UNION ALL
SELECT 'patient_breed_species_mismatch', COUNT(*)
FROM patients p JOIN breeds b ON b.id=p.breed_id
WHERE b.species_id <> p.species_id
UNION ALL
SELECT 'evaluations_no_patient', COUNT(*)
FROM evaluations e LEFT JOIN patients p ON p.id=e.patient_id
WHERE p.id IS NULL
UNION ALL
SELECT 'results_no_evaluation', COUNT(*)
FROM inference_results r LEFT JOIN evaluations e ON e.id=r.evaluation_id
WHERE e.id IS NULL
UNION ALL
SELECT 'results_no_disease', COUNT(*)
FROM inference_results r LEFT JOIN diseases d ON d.id=r.disease_id
WHERE d.id IS NULL
UNION ALL
SELECT 'results_no_risk_level', COUNT(*)
FROM inference_results r LEFT JOIN risk_levels rl ON rl.id=r.risk_level_id
WHERE rl.id IS NULL
UNION ALL
SELECT 'activated_rules_no_result', COUNT(*)
FROM activated_rules ar LEFT JOIN inference_results r ON r.id=ar.result_id
WHERE r.id IS NULL
UNION ALL
SELECT 'activated_rules_no_rule', COUNT(*)
FROM activated_rules ar LEFT JOIN inference_rules r ON r.id=ar.rule_id
WHERE r.id IS NULL
UNION ALL
SELECT 'result_probability_out_of_range', COUNT(*)
FROM inference_results
WHERE probability < 0 OR probability > 1
UNION ALL
SELECT 'clinical_probability_out_of_range', COUNT(*)
FROM clinical_probabilities
WHERE probability_given_disease < 0 OR probability_given_disease > 1
   OR general_probability < 0 OR general_probability > 1;
```

## 9. Script automatizado

Ejecutar:

```powershell
$env:DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5433/vet_inference'
.\.venv\Scripts\python.exe tests\e2e_backend_flow.py
```

Resultado obtenido:

```text
Checks aprobados: 11
Checks fallidos : 0
Exito           : 100.00%
```

## 10. Guia Swagger/Postman

1. Abrir `/docs`.
2. Ejecutar `POST /api/v1/auth/login`.
3. Copiar `access_token`.
4. En Swagger, pulsar `Authorize` y colocar `Bearer <token>`.
5. Ejecutar `GET /api/v1/species` y copiar `id` de Perro.
6. Ejecutar `GET /api/v1/breeds?species_id=1` y copiar `id` de Poodle.
7. Ejecutar `POST /api/v1/owners/` y copiar `owner_id`.
8. Ejecutar `POST /api/v1/patients` usando `owner_id`, `species_id` y `breed_id`.
9. Ejecutar `POST /api/v1/evaluations` con los `facts`.
10. Ejecutar `POST /api/v1/evaluaciones/{evaluation_id}/procesar`.
11. Ejecutar `GET /api/v1/evaluations/{evaluation_id}/results`.
12. Copiar `result_id` del resultado Diabetes mellitus.
13. Ejecutar `GET /api/v1/results/{result_id}/activated-rules`.
14. Ejecutar `GET /api/v1/patients/{patient_id}/history`.

## 11. Criterios de aceptacion

Paso 6 aprobado si:

- Login devuelve JWT.
- Se crea owner.
- Se crea patient asociado a owner/species/breed.
- Se crea evaluation con facts.
- Se procesan reglas + Bayes.
- Se persisten resultados.
- Se persisten reglas activadas.
- El resultado contiene enfermedad, probabilidad, nivel de riesgo, explicacion y reglas activadas.
- El historial muestra evaluacion y resultado.
- No hay registros huerfanos.
- Swagger/Postman puede reproducir el flujo.

## 12. Errores comunes

| Error | Causa probable | Solucion |
| --- | --- | --- |
| 401 Unauthorized | JWT ausente, vencido o mal copiado | Rehacer login y usar `Bearer <token>` |
| 403 Forbidden | Rol insuficiente | Usar admin/veterinario |
| 404 owner/patient/evaluation not found | ID incorrecto | Copiar IDs de la respuesta anterior |
| 422 payload mal formado | Campo faltante o tipo incorrecto | Revisar schema en Swagger |
| Foreign key error | owner/species/breed inexistente | Consultar catalogos antes de crear |
| Breed no pertenece a species | breed_id de otra especie | Filtrar breeds por species_id |
| No hay reglas activas | `inference_rules.is_active=false` o faltan seeds | Revisar bootstrap/migraciones |
| No hay clinical_probabilities | tabla vacia | Ejecutar bootstrap o cargar seeds |
| Evaluacion sin facts | payload sin sintomas/variables | Enviar facts en `POST /evaluations` |
| Riesgo bajo inesperado | evidencia no coincide con reglas/probabilidades | Usar keys exactas: `glucosa`, `glucosuria`, `poliuria` |
| No se guardan activated_rules | reglas no se activaron | Verificar condiciones y valores esperados |

## 13. Evidencia para tesis

Guardar:

- Captura de Swagger login.
- Captura de creacion de owner/patient.
- Captura de creacion de evaluacion con facts.
- Captura de procesamiento de inferencia.
- Captura de resultados con probabilidad, riesgo y reglas.
- Captura de historial clinico.
- Salida de `tests/e2e_backend_flow.py`.
- Queries SQL de persistencia.
- Query de integridad con conteos en cero.

## 14. Tabla final de validacion

| ID | Modulo | Endpoint | Entrada | Salida esperada | Salida obtenida | Estado | Evidencia |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E2E-01 | Auth | `/auth/login` | credenciales | JWT | JWT 200 | PASS | script |
| E2E-02 | Catalogos | `/species`, `/breeds` | JWT | Perro/Poodle | IDs 1/2 | PASS | script |
| E2E-03 | Owner | `/owners/` | owner JSON | owner_id | 2 | PASS | SQL/script |
| E2E-04 | Patient | `/patients` | patient JSON | patient_id | 3 | PASS | SQL/script |
| E2E-05 | Evaluation | `/evaluations` | facts | evaluation_id | 78 | PASS | SQL/script |
| E2E-06 | Inferencia | `/evaluaciones/78/procesar` | evaluation_id | Diabetes Alto | prob 0.6965, Alto | PASS | script |
| E2E-07 | Resultados | `/evaluations/78/results` | evaluation_id | persistencia | result_id 309 | PASS | SQL/script |
| E2E-08 | Reglas | `/results/309/activated-rules` | result_id | DM-R03/DM-R04 | ambas reglas | PASS | SQL/script |
| E2E-09 | Historial | `/patients/3/history` | patient_id | eventos clinicos | 2 eventos | PASS | SQL/script |
| E2E-10 | Integridad | SQL | N/A | 0 huerfanos | 0 en 11 checks | PASS | SQL |

## 15. Conclusion academica

Se valido el flujo completo end-to-end del backend API REST correspondiente al OE3, comprobando autenticacion mediante JWT, gestion de duenos y pacientes, registro de evaluaciones clinicas con sintomas y variables, procesamiento mediante motor hibrido de reglas IF-THEN y Bayes, persistencia de resultados, trazabilidad de reglas activadas e incorporacion al historial clinico. La ejecucion automatizada obtuvo 100% de exito y las consultas SQL confirmaron la integridad referencial y la ausencia de registros huerfanos, por lo que el backend queda validado como evidencia tecnica del desarrollo del OE3.
