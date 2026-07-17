import re
import unicodedata
from typing import Any

from app.core.config import settings
from app.core.constants import RISK_HIGH, RISK_LOW, RISK_MODERATE
from app.models.clinical_probability import ClinicalProbability
from app.models.disease import Disease


class BayesService:
    def __init__(self, db):
        self.db = db

    def obtener_evidencias_evaluacion(self, facts: dict) -> list[dict]:
        evidences = []
        for key, value in facts.items():
            if key in ["species_id", "patient_id", "evaluation_id", "id"]:
                continue
            if key == "sintomas" and isinstance(value, list):
                for symptom in value:
                    evidences.append({"type": "symptom", "key": symptom.strip(), "value": True})
            elif key == "sintomas" and isinstance(value, str):
                for symptom in value.split(","):
                    symptom_clean = symptom.strip()
                    if symptom_clean:
                        evidences.append({"type": "symptom", "key": symptom_clean, "value": True})
            elif isinstance(value, bool) or str(value).lower() in ["true", "false", "si", "no"]:
                is_present = str(value).lower() in ["true", "si"]
                evidences.append({"type": "symptom", "key": key.strip(), "value": is_present})
            else:
                evidences.append({"type": "variable", "key": key.strip(), "value": value})
        return evidences

    def evaluar_reglas(self, engine, facts: dict, rules: list) -> list[dict]:
        return engine.evaluate(facts=facts, rules=rules)

    def _normalize_name(self, text: str) -> str:
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKD", text.strip().lower())
        text_without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
        return text_without_accents.replace("_", " ").replace("-", " ")

    def _check_variable_value(self, observed_value: Any, expected_value: str | None) -> bool:
        if expected_value is None:
            return True
        obs_str = self._normalize_name(str(observed_value))
        exp_str = self._normalize_name(str(expected_value))

        match = re.match(r"^([><]=?)\s*([0-9.]+)", exp_str)
        if match:
            op, val_str = match.groups()
            try:
                obs_num = float(observed_value)
                exp_num = float(val_str)
            except (ValueError, TypeError):
                return False
            if op == ">":
                return obs_num > exp_num
            if op == ">=":
                return obs_num >= exp_num
            if op == "<":
                return obs_num < exp_num
            if op == "<=":
                return obs_num <= exp_num

        return obs_str == exp_str or exp_str in obs_str

    def calcular_probabilidad_bayes(
        self,
        disease: Disease,
        evidences: list[dict],
        clinical_probs: list[ClinicalProbability],
    ) -> float:
        likelihood = disease.base_probability if disease.base_probability is not None else settings.bayes_default_prior

        for evidence in evidences:
            if evidence["type"] == "symptom" and not evidence["value"]:
                continue

            matched_prob = None
            evidence_key_norm = self._normalize_name(evidence["key"])

            for prob in clinical_probs:
                if not prob.is_active or prob.disease_id != disease.id:
                    continue

                if evidence["type"] == "symptom" and prob.symptom_id is not None:
                    symptom_name_norm = self._normalize_name(prob.symptom.name)
                    if (
                        symptom_name_norm == evidence_key_norm
                        or evidence_key_norm in symptom_name_norm
                        or symptom_name_norm in evidence_key_norm
                    ):
                        matched_prob = prob
                        break
                elif evidence["type"] == "variable" and prob.variable_id is not None:
                    var_key_norm = self._normalize_name(prob.variable.key)
                    var_name_norm = self._normalize_name(prob.variable.name)
                    if var_key_norm == evidence_key_norm or var_name_norm == evidence_key_norm:
                        if self._check_variable_value(evidence["value"], prob.expected_value):
                            matched_prob = prob
                            break

            likelihood *= (
                matched_prob.probability_given_disease
                if matched_prob is not None
                else settings.bayes_smoothing_factor
            )

        return likelihood

    def normalizar_probabilidades(self, resultados: list[dict]) -> list[dict]:
        total_likelihood = sum(r["likelihood"] for r in resultados)
        if total_likelihood <= 0:
            n_results = len(resultados)
            for r in resultados:
                r["probability"] = round(1.0 / n_results, settings.probability_precision)
            return resultados

        for r in resultados:
            prob = r["likelihood"] / total_likelihood
            r["probability"] = round(max(0.0, min(1.0, prob)), settings.probability_precision)
        return resultados

    def determinar_nivel_riesgo(self, probabilidad: float, reglas_activadas: list[dict]) -> str:
        """Clasifica exclusivamente por el porcentaje de probabilidad acordado.

        Las reglas IF-THEN aportan la evidencia trazable de la conclusión, pero no
        pueden elevar un resultado fuera de los rangos publicados al veterinario.
        """
        return self._risk_from_probability(probabilidad)

    def _risk_from_probability(self, probabilidad: float) -> str:
        probability = max(0.0, min(1.0, probabilidad))
        if probability >= 0.70:
            return RISK_HIGH.capitalize()
        if probability >= 0.40:
            return RISK_MODERATE.capitalize()
        return RISK_LOW.capitalize()

    def generar_explicacion_bayes(
        self,
        disease_name: str,
        probabilidad: float,
        reglas_activadas: list[dict],
        evidencias: list[dict],
    ) -> str:
        sintomas_detectados = [e["key"] for e in evidencias if e["type"] == "symptom" and e["value"]]
        variables_detectadas = [f"{e['key']} ({e['value']})" for e in evidencias if e["type"] == "variable"]

        explicacion = (
            f"Analisis probabilistico bayesiano para {disease_name} "
            f"con una probabilidad calculada de {probabilidad * 100:.2f}%. "
        )

        nivel_riesgo = self._risk_from_probability(probabilidad)
        rango_riesgo = {
            "Bajo": "0% a menos de 40%",
            "Moderado": "40% a menos de 70%",
            "Alto": "70% a 100%",
        }[nivel_riesgo]
        explicacion += f"El porcentaje se clasifica como riesgo {nivel_riesgo.lower()} ({rango_riesgo}). "

        matched_evidences = []
        if sintomas_detectados:
            matched_evidences.append(f"sintomas observados: {', '.join(sintomas_detectados)}")
        if variables_detectadas:
            matched_evidences.append(f"variables clinicas registradas: {', '.join(variables_detectadas)}")

        if matched_evidences:
            explicacion += f"Evidencias clinicas consideradas: {'; '.join(matched_evidences)}. "

        if reglas_activadas:
            codigos_reglas = [r["rule_code"] for r in reglas_activadas]
            explicacion += (
                f"Las reglas IF-THEN activadas ({', '.join(codigos_reglas)}) "
                "sustentan la evidencia clinica registrada para esta inferencia."
            )
        else:
            explicacion += (
                "No se activaron reglas clinicas de soporte directas; "
                "el riesgo es estimado por perfil bayesiano."
            )

        return explicacion
