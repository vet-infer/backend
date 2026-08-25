from app.core.constants import normalize_risk_level
from app.models.risk_level import RiskLevel
from app.repositories.base import BaseRepository


class RiskLevelRepository(BaseRepository[RiskLevel]):
    model = RiskLevel

    def list_active(self) -> list[RiskLevel]:
        return (
            self.db.query(RiskLevel)
            .filter(RiskLevel.is_active.is_(True))
            .order_by(RiskLevel.sort_order)
            .all()
        )

    def get_by_code(self, code: str) -> RiskLevel | None:
        return self.db.query(RiskLevel).filter(RiskLevel.code == code).first()

    def get_or_create(self, code: str) -> RiskLevel:
        normalized_code = normalize_risk_level(code)
        risk_level = self.get_by_code(normalized_code)
        if risk_level is not None:
            return risk_level

        risk_level = RiskLevel(
            code=normalized_code,
            name=normalized_code.capitalize(),
            description="Nivel de riesgo clinico definido por el sistema.",
            sort_order=99,
            is_active=True,
        )
        self.db.add(risk_level)
        self.db.commit()
        self.db.refresh(risk_level)
        return risk_level
