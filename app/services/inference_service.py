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
        rules = self.rule_repository.get_active_rules_by_species(patient.species_id)
        return self.engine.evaluate(facts=facts, rules=rules)

    def run_and_persist(self, evaluation_id: int) -> list:
        evaluation = self.evaluation_repository.get_with_facts(evaluation_id)
        if evaluation is None:
            raise NotFoundError("Evaluacion no encontrada")
        facts = {fact.fact_key: fact.value for fact in evaluation.facts}
        facts.setdefault("species_id", evaluation.patient.species_id)

        rules = self.rule_repository.get_active_rules_by_species(evaluation.patient.species_id)
        results = self.engine.evaluate(facts=facts, rules=rules)
        persistence_payload = [
            {
                "disease_id": result["disease_id"],
                "suggested_diagnosis": result["suggested_diagnosis"],
                "risk_level": result["risk_level"],
                "score": result["score"],
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

    def list_results(self, evaluation_id: int):
        return self.result_repository.list_by_evaluation(evaluation_id)

    def list_activated_rules(self, result_id: int):
        return self.result_repository.list_activated_rules(result_id)
