def risk_from_score(score: float) -> str:
    if score >= 7:
        return "alto"
    if score >= 4:
        return "moderado"
    return "bajo"
