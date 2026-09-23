"""Genera alembic/data/demo_clinical_history.json para la migracion de datos demo.

Define propietarios, pacientes y evaluaciones historicas, valida los hechos contra
fact_definitions y ejecuta el motor hibrido (reglas + Bayes) para precalcular los
resultados. La migracion solo inserta el JSON, asi no depende del codigo de la app.

Uso (requiere la base con la base de conocimiento cargada):
    docker compose exec api python scripts/generate_demo_history.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.patient import Patient  # noqa: F401  (registra mappers)
from app.models.species import Species
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.result_repository import ResultRepository
from app.repositories.rule_repository import RuleRepository
from app.services.evaluation_service import EvaluationService
from app.services.inference_service import InferenceService

OUTPUT = Path(__file__).resolve().parents[1] / "alembic" / "data" / "demo_clinical_history.json"

OWNERS = [
    {"key": "quispe", "first_name": "María Fernanda", "last_name": "Quispe Huamán", "phone": "987654321",
     "email": "maria.quispe.demo@example.com", "document_type": "DNI", "document_number": "45872136",
     "address": "Av. Arequipa 1450, Dpto. 302", "district": "Lince", "ubigeo": "150116",
     "created_at": "2025-09-18T10:12:00-05:00"},
    {"key": "rojas", "first_name": "Carlos Alberto", "last_name": "Rojas Paredes", "phone": "956321478",
     "email": "carlos.rojas.demo@example.com", "document_type": "DNI", "document_number": "40125589",
     "address": "Jr. Las Begonias 230", "district": "San Isidro", "ubigeo": "150131",
     "created_at": "2025-09-25T16:40:00-05:00"},
    {"key": "mendoza", "first_name": "Lucía", "last_name": "Mendoza Castillo", "phone": "912458736",
     "email": "lucia.mendoza.demo@example.com", "document_type": "DNI", "document_number": "47789012",
     "address": "Calle Los Pinos 118", "district": "Miraflores", "ubigeo": "150122",
     "created_at": "2025-10-07T09:05:00-05:00"},
    {"key": "chavez", "first_name": "Jorge Luis", "last_name": "Chávez Ramírez", "phone": "998127456",
     "email": "jorge.chavez.demo@example.com", "document_type": "DNI", "document_number": "41236674",
     "address": "Av. La Marina 2200", "district": "San Miguel", "ubigeo": "150136",
     "created_at": "2025-11-12T11:30:00-05:00"},
    {"key": "torres", "first_name": "Ana Sofía", "last_name": "Torres Vega", "phone": "945782163",
     "email": "ana.torres.demo@example.com", "document_type": "DNI", "document_number": "72345618",
     "address": "Av. Alfredo Benavides 3050", "district": "Santiago de Surco", "ubigeo": "150140",
     "created_at": "2025-12-03T15:20:00-05:00"},
    {"key": "salazar", "first_name": "Ricardo", "last_name": "Salazar Núñez", "phone": "934567812",
     "email": "ricardo.salazar.demo@example.com", "document_type": "CE", "document_number": "001234567",
     "address": "Av. Javier Prado Este 4200", "district": "La Molina", "ubigeo": "150114",
     "created_at": "2026-01-14T10:00:00-05:00"},
    {"key": "gutierrez", "first_name": "Rosa Elena", "last_name": "Gutiérrez Flores", "phone": "976543218",
     "email": "rosa.gutierrez.demo@example.com", "document_type": "DNI", "document_number": "09874521",
     "address": "Jr. Huiracocha 1765", "district": "Jesús María", "ubigeo": "150113",
     "created_at": "2026-02-09T17:45:00-05:00"},
    {"key": "vargas", "first_name": "Diego Alonso", "last_name": "Vargas León", "phone": "923456789",
     "email": "diego.vargas.demo@example.com", "document_type": "DNI", "document_number": "70458823",
     "address": "Av. Universitaria 1800", "district": "Los Olivos", "ubigeo": "150117",
     "created_at": "2026-03-02T12:10:00-05:00"},
]

PATIENTS = [
    {"key": "rocky", "owner": "quispe", "name": "Rocky", "species": "Perro", "breed": "Golden Retriever",
     "sex": "Macho", "birth_date": "2014-03-10", "weight": 32.5, "created_at": "2025-09-18T10:20:00-05:00"},
    {"key": "mishi", "owner": "quispe", "name": "Mishi", "species": "Gato", "breed": "Siamese",
     "sex": "Hembra", "birth_date": "2011-02-14", "weight": 3.9, "created_at": "2025-09-18T10:25:00-05:00"},
    {"key": "luna", "owner": "rojas", "name": "Luna", "species": "Perro", "breed": "Poodle",
     "sex": "Hembra", "birth_date": "2012-06-02", "weight": 6.8, "created_at": "2025-09-25T16:50:00-05:00"},
    {"key": "olivia", "owner": "rojas", "name": "Olivia", "species": "Gato", "breed": "Maine Coon",
     "sex": "Hembra", "birth_date": "2018-03-03", "weight": 6.2, "created_at": "2026-04-06T09:15:00-05:00"},
    {"key": "toby", "owner": "mendoza", "name": "Toby", "species": "Perro", "breed": "Beagle",
     "sex": "Macho", "birth_date": "2017-09-20", "weight": 16.4, "created_at": "2025-10-07T09:15:00-05:00"},
    {"key": "simba", "owner": "mendoza", "name": "Simba", "species": "Gato", "breed": "European Shorthair",
     "sex": "Macho", "birth_date": "2020-05-01", "weight": 5.1, "created_at": "2025-11-20T18:00:00-05:00"},
    {"key": "kira", "owner": "chavez", "name": "Kira", "species": "Perro", "breed": "German Shepherd Dog",
     "sex": "Hembra", "birth_date": "2019-01-15", "weight": 29.0, "created_at": "2025-11-12T11:40:00-05:00"},
    {"key": "max", "owner": "torres", "name": "Max", "species": "Perro", "breed": "Chihuahua",
     "sex": "Macho", "birth_date": "2013-11-05", "weight": 3.2, "created_at": "2025-12-03T15:30:00-05:00"},
    {"key": "garfield", "owner": "torres", "name": "Garfield", "species": "Gato", "breed": "No definido",
     "sex": "Macho", "birth_date": "2014-07-07", "weight": 7.8, "created_at": "2026-02-18T10:30:00-05:00"},
    {"key": "nala", "owner": "salazar", "name": "Nala", "species": "Gato", "breed": "Persian",
     "sex": "Hembra", "birth_date": "2012-10-10", "weight": 3.4, "created_at": "2026-01-14T10:10:00-05:00"},
    {"key": "canela", "owner": "gutierrez", "name": "Canela", "species": "Perro", "breed": "No definido",
     "sex": "Hembra", "birth_date": "2016-04-12", "weight": 18.2, "created_at": "2026-02-09T17:55:00-05:00"},
    {"key": "bruno", "owner": "vargas", "name": "Bruno", "species": "Perro", "breed": "Shih Tzu",
     "sex": "Macho", "birth_date": "2015-08-08", "weight": 7.5, "created_at": "2026-03-02T12:20:00-05:00"},
    {"key": "tom", "owner": "vargas", "name": "Tom", "species": "Gato", "breed": "British Shorthair",
     "sex": "Macho", "birth_date": "2016-12-01", "weight": 5.5, "created_at": "2026-03-02T12:25:00-05:00"},
]

ERC_PERRO = {"edad avanzada": True, "poliuria": True, "polidipsia": True, "perdida de peso": True,
             "disminucion del apetito": True, "letargo": True}
PERIODONTAL_PERRO = {"halitosis": True, "sangrado gingival": True, "recesion gingival": True,
                     "dificultad para masticar": True, "raza pequena": True}

EVALUATIONS = [
    # Rocky: ERC canina diagnosticada y seguimiento.
    {"patient": "rocky", "created_at": "2025-10-02T10:30:00-05:00", "reason": "Toma mucha agua y orina seguido",
     "observations": "Paciente geriátrico con pérdida de peso progresiva en los últimos dos meses.",
     "facts": {**ERC_PERRO, "creatinina": 2.4, "sdma": 19, "bun": 48, "densidad_urinaria": 1.014, "upc": 0.6}},
    {"patient": "rocky", "created_at": "2026-01-15T11:00:00-05:00", "reason": "Control de función renal",
     "observations": "En dieta renal desde octubre. Propietaria refiere menor apetito.",
     "facts": {**ERC_PERRO, "creatinina": 3.1, "sdma": 26, "bun": 62, "densidad_urinaria": 1.011, "upc": 0.9,
               "fosforo_inorganico": 6.4, "hallazgos_ecograficos_renales": "compatibles con ERC"}},
    {"patient": "rocky", "created_at": "2026-06-20T09:40:00-05:00", "reason": "Control trimestral renal",
     "observations": "Estable con dieta renal y quelante de fósforo.",
     "facts": {"edad avanzada": True, "poliuria": True, "polidipsia": True, "creatinina": 2.9, "sdma": 23,
               "bun": 55, "fosforo_inorganico": 5.1, "hallazgos_ecograficos_renales": "compatibles con ERC"}},
    # Mishi: ERC felina.
    {"patient": "mishi", "created_at": "2025-11-05T16:15:00-05:00", "reason": "Vómitos y baja de peso",
     "observations": "Gata senior, pelaje descuidado.",
     "facts": {"edad avanzada": True, "poliuria": True, "polidipsia": True, "perdida de peso": True,
               "vomito": True, "disminucion del apetito": True, "creatinina": 3.2, "sdma": 25,
               "densidad_urinaria": 1.018, "upc": 0.5, "hallazgos_ecograficos_renales": "compatibles con ERC"}},
    {"patient": "mishi", "created_at": "2026-05-12T15:30:00-05:00", "reason": "Control renal",
     "observations": "Mejor apetito con fluidoterapia subcutánea.",
     "facts": {"edad avanzada": True, "poliuria": True, "polidipsia": True, "creatinina": 2.7, "sdma": 21,
               "densidad_urinaria": 1.020}},
    # Luna: MMVD con progresión.
    {"patient": "luna", "created_at": "2025-10-20T17:00:00-05:00", "reason": "Tos nocturna",
     "observations": "Soplo sistólico grado III/VI en foco mitral.",
     "facts": {"soplo cardiaco": True, "tos": True, "raza pequena": True, "edad avanzada": True,
               "intolerancia ejercicio": True, "la_ao": 1.7, "vhs": 11.2, "nt_probnp": 1200}},
    {"patient": "luna", "created_at": "2026-03-18T18:20:00-05:00", "reason": "Dificultad respiratoria",
     "observations": "Progresión del soplo a grado IV/VI. Episodio de síncope referido.",
     "facts": {"soplo cardiaco": True, "tos": True, "raza pequena": True, "edad avanzada": True,
               "intolerancia ejercicio": True, "disnea": True, "sincope": True, "la_ao": 2.1, "vhs": 12.4,
               "nt_probnp": 2400, "lviddn": 2.0}},
    # Toby: hipotiroidismo.
    {"patient": "toby", "created_at": "2025-10-28T09:45:00-05:00", "reason": "Aumento de peso y caída de pelo",
     "observations": "Alopecia en flancos, busca lugares cálidos.",
     "facts": {"aumento de peso": True, "letargo": True, "alopecia simetrica": True,
               "intolerancia al frio": True, "piel seca": True, "t4_total": 0.7}},
    {"patient": "toby", "created_at": "2026-04-22T10:10:00-05:00", "reason": "Control anual",
     "observations": "En tratamiento con levotiroxina, recuperó pelaje.",
     "facts": {"aumento de peso": False, "letargo": False, "t4_total": 2.3}},
    # Kira: otitis externa.
    {"patient": "kira", "created_at": "2025-12-10T12:00:00-05:00", "reason": "Se rasca las orejas",
     "observations": "Secreción marrón en oído izquierdo.",
     "facts": {"rascado de oidos": True, "sacudida de cabeza": True, "mal olor otico": True,
               "secrecion otica": True, "eritema del pabellon auricular": True, "citologia_otica": "positiva"}},
    # Max: enfermedad periodontal.
    {"patient": "max", "created_at": "2025-12-15T16:30:00-05:00", "reason": "Mal aliento",
     "observations": "Cálculo dental abundante, piezas premolares con movilidad.",
     "facts": {**PERIODONTAL_PERRO, "movilidad dental": True, "dolor oral": True, "edad avanzada": True,
               "grado_gingivitis": "severa", "placa": "severa", "porphyromonas": "detectado",
               "treponema": "detectado", "qpcr_placa": "positiva"}},
    # Simba: leucemia viral felina.
    {"patient": "simba", "created_at": "2025-11-20T18:15:00-05:00", "reason": "Decaído y con fiebre",
     "observations": "Gato con salida libre al exterior, esquema de vacunación incompleto.",
     "facts": {"acceso al exterior": True, "baja vacunacion": True, "convivencia con gatos positivos": True,
               "fiebre recurrente": True, "letargo": True, "anemia": True, "snap_felv": "positivo",
               "felv_p27": "positivo"}},
    {"patient": "simba", "created_at": "2026-02-26T17:40:00-05:00", "reason": "Infecciones repetidas",
     "observations": "Tercer cuadro infeccioso en tres meses.",
     "facts": {"acceso al exterior": True, "infecciones recurrentes": True, "fiebre recurrente": True,
               "anemia": True, "perdida de peso": True, "snap_felv": "positivo", "felv_p27": "positivo",
               "clasificacion_felv": "high positive", "carga_proviral_qpcr": 1250000, "coinfeccion_fiv": "negativa"}},
    # Nala: hipertiroidismo felino.
    {"patient": "nala", "created_at": "2026-01-14T10:30:00-05:00", "reason": "Come mucho pero adelgaza",
     "observations": "Nódulo tiroideo palpable. Inquieta durante la consulta.",
     "facts": {"perdida de peso": True, "polifagia": True, "hiperactividad": True, "taquicardia": True,
               "edad avanzada": True, "vomito": True, "t4_total": 7.9}},
    # Canela: diabetes mellitus canina.
    {"patient": "canela", "created_at": "2026-02-09T18:10:00-05:00", "reason": "Bebe y orina en exceso",
     "observations": "Hembra entera, apetito aumentado.",
     "facts": {"poliuria": True, "polidipsia": True, "polifagia": True, "perdida de peso": True,
               "glucosa": 320, "fructosamina": 520, "glucosuria": "positiva", "hemoglobina_glucosilada": 7.4}},
    {"patient": "canela", "created_at": "2026-07-08T11:25:00-05:00", "reason": "Control glucémico",
     "observations": "Con insulina NPH dos veces al día. Buen control.",
     "facts": {"poliuria": False, "polidipsia": False, "glucosa": 165, "fructosamina": 390,
               "glucosuria": "negativa"}},
    # Garfield: diabetes felina.
    {"patient": "garfield", "created_at": "2026-02-18T10:45:00-05:00", "reason": "Orina fuera del arenero",
     "observations": "Gato con sobrepeso previo, ahora en descenso.",
     "facts": {"poliuria": True, "polidipsia": True, "polifagia": True, "perdida de peso": True,
               "glucosa": 380, "fructosamina": 560, "glucosuria": "positiva"}},
    # Bruno: enfermedad periodontal y luego otitis externa.
    {"patient": "bruno", "created_at": "2026-03-02T12:40:00-05:00", "reason": "Sangrado de encías",
     "observations": "Gingivitis generalizada.",
     "facts": {**PERIODONTAL_PERRO, "grado_gingivitis": "moderada", "placa": "moderada",
               "porphyromonas": "detectado"}},
    {"patient": "bruno", "created_at": "2026-08-14T15:00:00-05:00", "reason": "Sacude la cabeza",
     "observations": "Oído derecho eritematoso tras baño.",
     "facts": {"rascado de oidos": True, "sacudida de cabeza": True, "eritema del pabellon auricular": True,
               "citologia_otica": "positiva"}},
    # Tom: chequeo geriatrico con ERC felina temprana.
    {"patient": "tom", "created_at": "2026-03-10T09:20:00-05:00", "reason": "Chequeo geriátrico",
     "observations": "Propietario nota que bebe algo más de agua. Sin otros signos.",
     "facts": {"edad avanzada": True, "polidipsia": True, "creatinina": 1.9, "sdma": 16,
               "densidad_urinaria": 1.030}},
    # Olivia: asma felina.
    {"patient": "olivia", "created_at": "2026-04-06T09:30:00-05:00", "reason": "Tos y respiración ruidosa",
     "observations": "Episodios de tos con cuello extendido.",
     "facts": {"tos": True, "sibilancias": True, "disnea": True, "intolerancia al ejercicio": True,
               "hallazgos_radiograficos_toracicos": "patron bronquial"}},
    {"patient": "olivia", "created_at": "2026-09-01T10:00:00-05:00", "reason": "Control respiratorio",
     "observations": "Con corticoide inhalado, episodios esporádicos.",
     "facts": {"tos": True, "sibilancias": False, "disnea": False,
               "hallazgos_radiograficos_toracicos": "patron bronquial"}},
]


def main() -> None:
    db = SessionLocal()
    try:
        species_ids = {s.name: s.id for s in db.query(Species).all()}
        patient_species = {p["key"]: species_ids[p["species"]] for p in PATIENTS}
        evaluation_service = EvaluationService(EvaluationRepository(db), PatientRepository(db))
        inference_service = InferenceService(
            RuleRepository(db), PatientRepository(db), EvaluationRepository(db), ResultRepository(db)
        )

        evaluations = []
        for evaluation in EVALUATIONS:
            species_id = patient_species[evaluation["patient"]]
            submitted = [
                SimpleNamespace(fact_key=key, value=value, source_type="clinical_input")
                for key, value in evaluation["facts"].items()
            ]
            facts = evaluation_service._validate_and_normalize_facts(submitted, species_id)
            results = inference_service._run_hybrid_inference(
                species_id, {**evaluation["facts"], "species_id": species_id}
            )
            evaluations.append(
                {
                    **{k: v for k, v in evaluation.items() if k != "facts"},
                    "facts": facts,
                    "results": [
                        {
                            "disease": result["disease"],
                            "suggested_diagnosis": result["suggested_diagnosis"],
                            "risk_level": result["risk_level"],
                            "score": result["score"],
                            "probability": result["probability"],
                            "inference_method": result["inference_method"],
                            "explanation": result["explanation"],
                            "activated_rules": [
                                {
                                    "rule_code": rule.get("rule_code"),
                                    "rule_version": rule.get("rule_version"),
                                    "fulfilled_conditions": rule["fulfilled_conditions"],
                                    "justification": rule["justification"],
                                }
                                for rule in result["activated_rules"]
                            ],
                        }
                        for result in results
                    ],
                }
            )
    finally:
        db.close()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"owners": OWNERS, "patients": PATIENTS, "evaluations": evaluations}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(evaluations)} evaluaciones escritas en {OUTPUT}")
    for evaluation in evaluations:
        top = evaluation["results"][0] if evaluation["results"] else None
        if top:
            print(f"  {evaluation['patient']:<9} {top['disease']:<40} {top['probability']:.2%} {top['risk_level']}")


if __name__ == "__main__":
    main()
