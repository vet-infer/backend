from dataclasses import dataclass


@dataclass(frozen=True)
class ConditionTrace:
    variable_key: str
    operator: str
    expected_value: object
    observed_value: object

    def as_text(self) -> str:
        return (
            f"{self.variable_key} {self.operator} {self.expected_value} "
            f"(observado: {self.observed_value})"
        )
