from app.core.exceptions import NotFoundError
from app.inference.engine import InferenceEngine
from app.models.disease import Disease
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.clinical_probability_repository import ClinicalProbabilityRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.result_repository import ResultRepository
from app.repositories.rule_repository import RuleRepository
from app.services.bayes_service import BayesService


class InferenceService:
    def __init__(
        self,
        rule_repository: RuleRepository,
        patient_repository: PatientRepository,
        evaluation_repository: EvaluationRepository,
        result_repository: ResultRepository,
        engine: InferenceEngine | None = None,
    ):
        self.rule_repository = rule_repository
        self.patient_repository = patient_repository
        self.evaluation_repository = evaluation_repository
        self.result_repository = result_repository
        self.engine = engine or InferenceEngine()

        db = rule_repository.db
        self.probability_repository = ClinicalProbabilityRepository(db)
        self.catalog_repository = CatalogRepository(db)
        self.bayes_service = BayesService(db)

    def run_from_payload(self, patient_id: int, facts: dict) -> list[dict]:
        patient = self.patient_repository.get_with_species(patient_id)
        if patient is None:
            raise NotFoundError("Paciente no encontrado")
        facts.setdefault("species_id", patient.species_id)
        return self._run_hybrid_inference(patient.species_id, facts)

    def run_and_persist(self, evaluation_id: int) -> list:
        evaluation = self.evaluation_repository.get_with_facts(evaluation_id)
        if evaluation is None:
            raise NotFoundError("Evaluacion no encontrada")
        facts = {fact.fact_key: fact.value for fact in evaluation.facts}
        facts.setdefault("species_id", evaluation.patient.species_id)

        results = self._run_hybrid_inference(evaluation.patient.species_id, facts)
        persistence_payload = [
            {
                "disease_id": result["disease_id"],
                "suggested_diagnosis": result["suggested_diagnosis"],
                "risk_level": result["risk_level"],
                "score": result["score"],
                "probability": result["probability"],
                "inference_method": result["inference_method"],
                "explanation": result["explanation"],
                "activated_rules": result["activated_rules"],
            }
            for result in results
        ]
        return self.result_repository.create_results(
            evaluation_id=evaluation.id,
            patient_id=evaluation.patient_id,
            results=persistence_payload,
        )

    def _run_hybrid_inference(self, species_id: int, facts: dict) -> list[dict]:
        rules_results = self._evaluate_rules(species_id, facts)
        activated_by_disease = {r["disease_id"]: r["activated_rules"] for r in rules_results}

        evidences = self.bayes_service.obtener_evidencias_evaluacion(facts)
        species_diseases = self._diseases_for_species(species_id)
        if not species_diseases:
            return []

        likelihoods = self._compute_bayes_likelihoods(species_diseases, evidences)
        normalized = self.bayes_service.normalizar_probabilidades(likelihoods)

        results = self._build_hybrid_results(normalized, rules_results, activated_by_disease, evidences)
        return sorted(results, key=lambda r: r["probability"], reverse=True)

    def _evaluate_rules(self, species_id: int, facts: dict) -> list[dict]:
        rules = self.rule_repository.get_active_rules_by_species(species_id)
        return self.engine.evaluate(facts=facts, rules=rules)

    def _diseases_for_species(self, species_id: int) -> list[Disease]:
        diseases = self.catalog_repository.list_diseases()
        return [d for d in diseases if d.species_id == species_id]

    def _compute_bayes_likelihoods(self, diseases: list[Disease], evidences: list[dict]) -> list[dict]:
        probs = self.probability_repository.listar_por_enfermedades([d.id for d in diseases])
        return [
            {
                "disease_id": disease.id,
                "disease": disease.name,
                "disease_obj": disease,
                "likelihood": self.bayes_service.calcular_probabilidad_bayes(disease, evidences, probs),
            }
            for disease in diseases
        ]

    def _build_hybrid_results(
        self,
        normalized: list[dict],
        rules_results: list[dict],
        activated_by_disease: dict[int, list[dict]],
        evidences: list[dict],
    ) -> list[dict]:
        results = []
        for item in normalized:
            disease_id = item["disease_id"]
            probability = item["probability"]
            disease = item["disease_obj"]
            activated_rules = activated_by_disease.get(disease_id, [])

            rules_res = next((r for r in rules_results if r["disease_id"] == disease_id), None)
            results.append(
                {
                    "disease_id": disease_id,
                    "disease": disease.name,
                    "suggested_diagnosis": f"Diagnostico sugerido: posible riesgo asociado a {disease.name}",
                    "risk_level": self.bayes_service.determinar_nivel_riesgo(probability, activated_rules),
                    "score": rules_res["score"] if rules_res else 0.0,
                    "probability": probability,
                    "inference_method": "reglas_bayes",
                    "explanation": self.bayes_service.generar_explicacion_bayes(
                        disease.name, probability, activated_rules, evidences
                    ),
                    "activated_rules": activated_rules,
                }
            )
        return results

    def list_results(self, evaluation_id: int):
        return self.result_repository.list_by_evaluation(evaluation_id)

    def list_activated_rules(self, result_id: int):
        return self.result_repository.list_activated_rules(result_id)
