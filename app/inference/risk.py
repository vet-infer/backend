from app.core.config import settings


def risk_from_score(score: float) -> str:
    if score >= settings.inference_high_score_threshold:
        return "alto"
    if score >= settings.inference_moderate_score_threshold:
        return "moderado"
    return "bajo"
