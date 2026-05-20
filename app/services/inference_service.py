from app.core.exceptions import NotFoundError
from app.inference.engine import InferenceEngine
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.result_repository import ResultRepository
from app.repositories.rule_repository import RuleRepository


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
        from app.repositories.clinical_probability_repository import ClinicalProbabilityRepository
        from app.repositories.catalog_repository import CatalogRepository
        from app.services.bayes_service import BayesService

        db = self.rule_repository.db
        prob_repo = ClinicalProbabilityRepository(db)
        catalog_repo = CatalogRepository(db)
        bayes_svc = BayesService(db)

        # 1. Run IF-THEN rules
        rules = self.rule_repository.get_active_rules_by_species(species_id)
        rules_results = self.engine.evaluate(facts=facts, rules=rules)

        # Group activated rules by disease_id
        activated_by_disease = {r["disease_id"]: r["activated_rules"] for r in rules_results}

        # 2. Extract clinical evidences from facts
        evidences = bayes_svc.obtener_evidencias_evaluacion(facts)

        # 3. Fetch all diseases for this species
        diseases = catalog_repo.list_diseases()
        species_diseases = [d for d in diseases if d.species_id == species_id]

        if not species_diseases:
            return []

        # 4. Fetch all clinical probabilities
        probs = db.query(prob_repo.model).filter(prob_repo.model.is_active == True).all()

        # 5. Compute Naive Bayes likelihoods
        likelihoods = []
        for disease in species_diseases:
            likelihood = bayes_svc.calcular_probabilidad_bayes(disease, evidences, probs)
            likelihoods.append({
                "disease_id": disease.id,
                "disease": disease.name,
                "disease_obj": disease,
                "likelihood": likelihood
            })

        # 6. Normalize probabilities
        normalized = bayes_svc.normalizar_probabilidades(likelihoods)

        # 7. Build final hybrid results
        output = []
        for item in normalized:
            disease_id = item["disease_id"]
            prob = item["probability"]
            disease = item["disease_obj"]

            # Fetch rules activated for this disease
            activated_rules = activated_by_disease.get(disease_id, [])

            # Determine hybrid risk level
            risk_level = bayes_svc.determinar_nivel_riesgo(prob, activated_rules)

            # Generate clinical explanation
            explanation = bayes_svc.generar_explicacion_bayes(disease.name, prob, activated_rules, evidences)

            # Calculate score
            rules_res = next((r for r in rules_results if r["disease_id"] == disease_id), None)
            score = rules_res["score"] if rules_res else 0.0

            output.append({
                "disease_id": disease_id,
                "disease": disease.name,
                "suggested_diagnosis": f"Diagnostico sugerido: posible riesgo asociado a {disease.name}",
                "risk_level": risk_level,
                "score": score,
                "probability": prob,
                "inference_method": "reglas_bayes",
                "explanation": explanation,
                "activated_rules": activated_rules
            })

        # Sort by probability descending
        return sorted(output, key=lambda r: r["probability"], reverse=True)

    def list_results(self, evaluation_id: int):
        return self.result_repository.list_by_evaluation(evaluation_id)

    def list_activated_rules(self, result_id: int):
        return self.result_repository.list_activated_rules(result_id)
