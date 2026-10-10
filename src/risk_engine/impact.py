EVENT_BASE_IMPACT = {
    "Geopolitical": 7,
    "Macroeconomic": 6,
    "Credit Event": 7,
    "Merger/Acquisition": 5,
    "Product Launch": 3,
    "General Market": 2,
}


def score_impact(event_classification: str, sentiment_score: float) -> int:
    base = EVENT_BASE_IMPACT.get(event_classification, 2)
    severity_adjustment = round(abs(sentiment_score) * 2)
    return max(1, min(10, base + severity_adjustment))
