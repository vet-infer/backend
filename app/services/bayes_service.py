import re
from typing import Any
from app.models.disease import Disease
from app.models.clinical_probability import ClinicalProbability


class BayesService:
    def __init__(self, db):
        self.db = db

    def obtener_evidencias_evaluacion(self, facts: dict) -> list[dict]:
        """
        Extracts and normalizes clinical facts into a uniform list of clinical evidences.
        """
        evidences = []
        for key, value in facts.items():
            if key in ["species_id", "patient_id", "evaluation_id", "id"]:
                continue
            if key == "sintomas" and isinstance(value, list):
                for symptom in value:
                    evidences.append({
                        "type": "symptom",
                        "key": symptom.strip(),
                        "value": True
                    })
            elif key == "sintomas" and isinstance(value, str):
                for symptom in value.split(","):
                    symptom_clean = symptom.strip()
                    if symptom_clean:
                        evidences.append({
                            "type": "symptom",
                            "key": symptom_clean,
                            "value": True
                        })
            else:
                # Handle individual key-value pairs
                if isinstance(value, bool) or str(value).lower() in ["true", "false", "si", "no"]:
                    is_present = str(value).lower() in ["true", "si"]
                    evidences.append({
                        "type": "symptom",
                        "key": key.strip(),
                        "value": is_present
                    })
                else:
                    evidences.append({
                        "type": "variable",
                        "key": key.strip(),
                        "value": value
                    })
        return evidences

    def evaluar_reglas(self, engine, facts: dict, rules: list) -> list[dict]:
        """
        Evaluates IF-THEN rules and returns the activated ones.
        """
        return engine.evaluate(facts=facts, rules=rules)

    def _normalize_name(self, text: str) -> str:
        """
        Normalizes string to improve clinical evidence matching.
        """
        if not text:
            return ""
        # Remove spaces, lowercase, and basic accents
        t = text.strip().lower()
        t = re.sub(r'[áäâà]', 'a', t)
        t = re.sub(r'[éëêè]', 'e', t)
        t = re.sub(r'[íïîì]', 'i', t)
        t = re.sub(r'[óöôò]', 'o', t)
        t = re.sub(r'[úüûù]', 'u', t)
        t = t.replace('_', ' ').replace('-', ' ')
        return t

    def _check_variable_value(self, observed_value: Any, expected_value: str | None) -> bool:
        """
        Evaluates variable values against conditional expected conditions (e.g. > 200, > 1.6, etc.)
        """
        if expected_value is None:
            return True
        obs_str = self._normalize_name(str(observed_value))
        exp_str = self._normalize_name(str(expected_value))

        # Check for numeric comparison operators: >, >=, <, <=
        match = re.match(r"^([><]=?)\s*([0-9.]+)", exp_str)
        if match:
            op, val_str = match.groups()
            try:
                obs_num = float(observed_value)
                exp_num = float(val_str)
                if op == ">":
                    return obs_num > exp_num
                elif op == ">=":
                    return obs_num >= exp_num
                elif op == "<":
                    return obs_num < exp_num
                elif op == "<=":
                    return obs_num <= exp_num
            except (ValueError, TypeError):
                return False

        return obs_str == exp_str or exp_str in obs_str

    def calcular_probabilidad_bayes(self, disease: Disease, evidences: list[dict], clinical_probs: list[ClinicalProbability]) -> float:
        """
        Calculates the posterior Naive Bayes likelihood for a disease given the clinical evidences.
        """
        prior = disease.base_probability if disease.base_probability is not None else 0.20
        likelihood = prior

        for evidence in evidences:
            # We only evaluate presence of symptoms or variable values
            if evidence["type"] == "symptom" and not evidence["value"]:
                continue

            matched_prob = None
            evidence_key_norm = self._normalize_name(evidence["key"])

            for prob in clinical_probs:
                if not prob.is_active or prob.disease_id != disease.id:
                    continue

                if evidence["type"] == "symptom" and prob.symptom_id is not None:
                    # Match by symptom name
                    symptom_name_norm = self._normalize_name(prob.symptom.name)
                    if symptom_name_norm == evidence_key_norm or evidence_key_norm in symptom_name_norm or symptom_name_norm in evidence_key_norm:
                        matched_prob = prob
                        break
                elif evidence["type"] == "variable" and prob.variable_id is not None:
                    # Match by variable key or name
                    var_key_norm = self._normalize_name(prob.variable.key)
                    var_name_norm = self._normalize_name(prob.variable.name)
                    if var_key_norm == evidence_key_norm or var_name_norm == evidence_key_norm:
                        # Also check the expected value
                        if self._check_variable_value(evidence["value"], prob.expected_value):
                            matched_prob = prob
                            break

            if matched_prob is not None:
                likelihood *= matched_prob.probability_given_disease
            else:
                # Laplace smoothing: use 0.5 (neutral uncertainty) when evidence is not registered for this disease
                likelihood *= 0.5

        return likelihood

    def normalizar_probabilidades(self, resultados: list[dict]) -> list[dict]:
        """
        Normalizes likelihoods so that they sum to exactly 1.0.
        """
        total_likelihood = sum(r["likelihood"] for r in resultados)
        if total_likelihood <= 0:
            # Fallback if all likelihoods are 0
            n_results = len(resultados)
            for r in resultados:
                r["probability"] = round(1.0 / n_results, 4)
            return resultados

        for r in resultados:
            prob = r["likelihood"] / total_likelihood
            r["probability"] = round(max(0.0, min(1.0, prob)), 4)
        return resultados

    def determinar_nivel_riesgo(self, probabilidad: float, reglas_activadas: list[dict]) -> str:
        """
        Determines the hybrid risk level by combining probability and rule severities.
        """
        has_high_rule = any(r.get("risk_level", "").lower() == "alto" for r in reglas_activadas)
        has_mod_rule = any(r.get("risk_level", "").lower() == "moderado" for r in reglas_activadas)

        # Base risk from probability
        if probabilidad >= 0.70:
            base_risk = "Alto"
        elif probabilidad >= 0.40:
            base_risk = "Moderado"
        else:
            base_risk = "Bajo"

        # Apply hybrid adjustments
        if base_risk == "Alto":
            return "Alto"

        if base_risk == "Moderado":
            if has_high_rule:
                return "Alto"
            return "Moderado"

        if base_risk == "Bajo":
            if has_high_rule:
                return "Moderado"
            elif has_mod_rule:
                return "Moderado"
            return "Bajo"

        return base_risk

    def generar_explicacion_bayes(self, disease_name: str, probabilidad: float, reglas_activadas: list[dict], evidencias: list[dict]) -> str:
        """
        Generates a readable clinical justification for the hybrid result.
        """
        sintomas_detectados = [e["key"] for e in evidencias if e["type"] == "symptom" and e["value"]]
        variables_detectadas = [f"{e['key']} ({e['value']})" for e in evidencias if e["type"] == "variable"]

        explicacion = f"Analisis probabilistico bayesiano para {disease_name} con una probabilidad calculada de {probabilidad * 100:.2f}%. "

        matched_evidences = []
        if sintomas_detectados:
            matched_evidences.append(f"sintomas observados: {', '.join(sintomas_detectados)}")
        if variables_detectadas:
            matched_evidences.append(f"variables clinicas registradas: {', '.join(variables_detectadas)}")

        if matched_evidences:
            explicacion += f"Evidencias clinicas consideradas: {'; '.join(matched_evidences)}. "

        if reglas_activadas:
            codigos_reglas = [r["rule_code"] for r in reglas_activadas]
            explicacion += f"Se activaron las reglas clinicas de soporte: {', '.join(codigos_reglas)}."
        else:
            explicacion += "No se activaron reglas clinicas de soporte directas, el riesgo es estimado unicamente por perfil bayesiano."

        return explicacion
