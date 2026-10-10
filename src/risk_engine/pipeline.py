from typing import Any
import logging

from src.risk_engine.classification import classify_event
from src.risk_engine.alpha_vantage import alpha_status, fetch_alpha_records
from src.risk_engine.impact import score_impact
from src.risk_engine.ingestion import LiveSourceError, fetch_live_records, live_collector
from src.risk_engine.normalization import normalize_record
from src.risk_engine.sentiment import analyze_sentiment, sentiment_status
from src.simulation import simulation_records


def analyze_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_record(record)
    sentiment, sentiment_confidence = analyze_sentiment(normalized["text"])
    event = classify_event(normalized["text"])
    return {
        **normalized,
        "sentiment_score": sentiment,
        "sentiment_confidence": sentiment_confidence,
        "event_classification": event,
        "impact_score": score_impact(event, sentiment),
        "analysis_method": (
            f"{sentiment_status()['backend']} sentiment; heuristic event and impact estimates"
        ),
    }


def analyze_text(text: str) -> dict[str, Any]:
    return analyze_record({"text": text})


def get_signals(mode: str = "live", query: str = "finance") -> list[dict[str, Any]]:
    if mode not in {"live", "hybrid"}:
        raise ValueError("Supported modes are live and hybrid; legacy synthetic fixtures are disabled")
    alpha_records = fetch_alpha_records()
    try:
        records = (live_collector.records() if live_collector.running else fetch_live_records(query=query)) + alpha_records
    except LiveSourceError as error:
        if not alpha_records and mode == "live":
            raise
        logging.getLogger(__name__).warning("Live RSS unavailable: %s", error)
        records = alpha_records
    if not records and mode == "live":
        raise LiveSourceError(alpha_status()["message"])
    signals = [analyze_record({**record, "data_origin": "live_publisher"}) for record in records]
    if mode == "hybrid":
        signals.extend(analyze_record(record) for record in simulation_records())
    return signals
