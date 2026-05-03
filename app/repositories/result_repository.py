from sqlalchemy.orm import joinedload

from app.models.clinical_history import ClinicalHistory
from app.models.inference_result import ActivatedRule, InferenceResult


class ResultRepository:
    def __init__(self, db):
        self.db = db

    def create_results(
        self,
        evaluation_id: int,
        patient_id: int,
        results: list[dict],
    ) -> list[InferenceResult]:
        persisted: list[InferenceResult] = []
        for result_data in results:
            activated_payload = result_data.pop("activated_rules")
            result = InferenceResult(evaluation_id=evaluation_id, **result_data)
            result.activated_rules = [
                ActivatedRule(
                    rule_id=rule["rule_id"],
                    fulfilled_conditions=rule["fulfilled_conditions"],
                    justification=rule["justification"],
                )
                for rule in activated_payload
            ]
            persisted.append(result)
            self.db.add(result)

        summary = f"Se generaron {len(persisted)} resultado(s) sugeridos por el motor de inferencia."
        self.db.add(
            ClinicalHistory(
                patient_id=patient_id,
                evaluation_id=evaluation_id,
                event_type="inference_result",
                summary=summary,
            )
        )
        self.db.commit()
        for result in persisted:
            self.db.refresh(result)
        return persisted

    def list_by_evaluation(self, evaluation_id: int) -> list[InferenceResult]:
        return (
            self.db.query(InferenceResult)
            .options(joinedload(InferenceResult.activated_rules))
            .filter(InferenceResult.evaluation_id == evaluation_id)
            .order_by(InferenceResult.score.desc())
            .all()
        )

    def list_activated_rules(self, result_id: int) -> list[ActivatedRule]:
        return (
            self.db.query(ActivatedRule)
            .filter(ActivatedRule.result_id == result_id)
            .all()
        )
