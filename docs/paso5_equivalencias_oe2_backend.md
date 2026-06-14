# Paso 5 - Equivalencias OE2 vs Backend

## Tabla de equivalencias

| Concepto OE2 / documento academico | Implementacion backend | Tipo | Justificacion tecnica |
| --- | --- | --- | --- |
| duenos | owners | Tabla | Se usa nombre en ingles por convencion tecnica del backend y ORM. |
| especies | species | Tabla | Catalogo normalizado para perros y gatos. |
| razas | breeds | Tabla | Catalogo normalizado dependiente de species. |
| pacientes | patients | Tabla | Entidad clinica evaluada. |
| enfermedades | diseases | Tabla | Catalogo de enfermedades degenerativas por especie. |
| niveles_riesgo | risk_levels | Tabla | Catalogo normalizado para bajo, moderado y alto. |
| sintomas | symptoms | Tabla | Catalogo de sintomas por especie. |
| variables_clinicas | clinical_variables | Tabla | Catalogo de variables medibles y observables. |
| evaluaciones_clinicas | evaluations | Tabla | Registro principal de evaluaciones clinicas. |
| evaluacion_sintomas | evaluation_facts | Tabla logica | Los sintomas se almacenan como facts clinicos para unificar sintomas y variables. |
| evaluation_variables | evaluation_facts | Tabla | Registro flexible de hechos clinicos de entrada. |
| evaluation_facts | evaluation_facts | Tabla | Nombre implementado directamente. |
| reglas_decision | inference_rules | Tabla | Reglas IF-THEN del motor de inferencia. |
| condiciones_regla | rule_conditions | Tabla | Condiciones evaluables asociadas a cada regla. |
| resultados_evaluacion | inference_results | Tabla | Resultados generados por reglas + Bayes para una evaluacion. |
| reglas_activadas | activated_rules | Tabla | Trazabilidad de reglas disparadas por resultado. |
| probabilidades_clinicas | clinical_probabilities | Tabla | Probabilidades condicionales usadas por Bayes. |
| probabilidad_base | diseases.base_probability | Columna | Probabilidad previa de enfermedad para Bayes. |
| probabilidad | inference_results.probability | Columna | Probabilidad posterior normalizada. |
| metodo_inferencia | inference_results.inference_method | Columna | Metodo utilizado, actualmente `reglas_bayes`. |

## Criterio de nomenclatura

El OE2 conserva nombres conceptuales en espanol para la trazabilidad academica. El backend implementa tablas y columnas en ingles por consistencia con FastAPI, SQLAlchemy, Alembic y convenciones de codigo. La equivalencia queda documentada para demostrar que no hay perdida funcional entre el modelo academico y el modelo fisico.

## Decision sobre niveles de riesgo

Se normaliza `risk_levels` como catalogo tecnico y academico. Las tablas `inference_rules` e `inference_results` conservan el campo textual `risk_level` por compatibilidad con la API existente, pero agregan `risk_level_id` como llave foranea hacia `risk_levels`.

Esta solucion mantiene estable el contrato actual del frontend y de las pruebas, mientras aporta integridad referencial, trazabilidad academica y posibilidad de administrar metadatos del nivel de riesgo.
