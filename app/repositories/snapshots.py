from dataclasses import dataclass


@dataclass
class DiseaseSnapshot:
    """Snapshot inmutable de una enfermedad, desacoplado de la sesion de
    SQLAlchemy que la cargo (ver app/inference/rule_view.py para el porque:
    un objeto ORM cacheado entre sesiones dispara DetachedInstanceError en
    cuanto SQLAlchemy expira sus atributos tras un commit en otra sesion)."""

    id: int
    name: str
    species_id: int
    description: str | None
    is_degenerative: bool
    is_active: bool
    base_probability: float | None

    @classmethod
    def from_orm_disease(cls, disease) -> "DiseaseSnapshot":
        return cls(
            id=disease.id,
            name=disease.name,
            species_id=disease.species_id,
            description=disease.description,
            is_degenerative=disease.is_degenerative,
            is_active=disease.is_active,
            base_probability=disease.base_probability,
        )


@dataclass
class _SymptomSnapshot:
    name: str


@dataclass
class _VariableSnapshot:
    key: str
    name: str


@dataclass
class ClinicalProbabilitySnapshot:
    """Snapshot inmutable de una ClinicalProbability, con `symptom`/`variable`
    como sub-objetos ya materializados (no relaciones perezosas de SQLAlchemy)
    para que BayesService pueda seguir accediendo a `.symptom.name` /
    `.variable.key` sin depender de una sesion abierta."""

    id: int
    disease_id: int
    symptom_id: int | None
    variable_id: int | None
    expected_value: object
    probability_given_disease: float
    general_probability: float
    is_active: bool
    symptom: _SymptomSnapshot | None
    variable: _VariableSnapshot | None

    @classmethod
    def from_orm_probability(cls, prob) -> "ClinicalProbabilitySnapshot":
        return cls(
            id=prob.id,
            disease_id=prob.disease_id,
            symptom_id=prob.symptom_id,
            variable_id=prob.variable_id,
            expected_value=prob.expected_value,
            probability_given_disease=prob.probability_given_disease,
            general_probability=prob.general_probability,
            is_active=prob.is_active,
            symptom=_SymptomSnapshot(name=prob.symptom.name) if prob.symptom is not None else None,
            variable=(
                _VariableSnapshot(key=prob.variable.key, name=prob.variable.name)
                if prob.variable is not None
                else None
            ),
        )
