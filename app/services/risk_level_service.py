from app.models.risk_level import RiskLevel
from app.repositories.risk_level_repository import RiskLevelRepository


class RiskLevelService:
    def __init__(self, repository: RiskLevelRepository):
        self.repository = repository

    def list_risk_levels(self) -> list[RiskLevel]:
        return self.repository.list_active()
