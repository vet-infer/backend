import json
from pathlib import Path


SEED_PATH = Path(__file__).resolve().parents[1] / "app" / "seeds" / "clinical_reference_data.json"
FELINE_DISEASES_REQUIRING_RULES = {"Enfermedad renal crónica", "Diabetes mellitus"}


def load_seed_data():
    return json.loads(SEED_PATH.read_text(encoding="utf-8-sig"))


def test_feline_renal_and_diabetes_have_if_then_rules_and_probabilities():
    seed_data = load_seed_data()

    feline_rules = [
        rule
        for rule in seed_data["rules"]
        if rule["species"] == "Gato" and rule["disease"] in FELINE_DISEASES_REQUIRING_RULES
    ]
    feline_probabilities = [
        probability
        for probability in seed_data["clinical_probabilities"]
        if probability["species"] == "Gato" and probability["disease"] in FELINE_DISEASES_REQUIRING_RULES
    ]

    assert {rule["disease"] for rule in feline_rules} == FELINE_DISEASES_REQUIRING_RULES
    assert {probability["disease"] for probability in feline_probabilities} == FELINE_DISEASES_REQUIRING_RULES
    assert all(rule["conditions"] for rule in feline_rules)


def test_feline_rule_conditions_use_registered_facts():
    seed_data = load_seed_data()
    feline_symptoms = {item["name"] for item in seed_data["symptoms"] if item["species"] == "Gato"}
    feline_variables = {item["key"] for item in seed_data["clinical_variables"] if item["species"] == "Gato"}
    feline_facts = feline_symptoms | feline_variables

    missing_facts = sorted(
        {
            condition["variable_key"]
            for rule in seed_data["rules"]
            if rule["species"] == "Gato" and rule["disease"] in FELINE_DISEASES_REQUIRING_RULES
            for condition in rule["conditions"]
            if condition["variable_key"] not in feline_facts
        }
    )

    assert missing_facts == []