from datetime import datetime, timezone
from typing import Any


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    text = str(record.get("text", "")).strip()
    if not text:
        raise ValueError("Record text must not be empty")

    raw_timestamp = record.get("timestamp")
    if raw_timestamp:
        timestamp = datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    entities = record.get("entities", [])
    if not isinstance(entities, list):
        raise ValueError("Record entities must be a list")

    return {
        "event_id": str(record.get("event_id") or "manual"),
        "source": str(record.get("source") or "manual"),
        "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "text": text,
        "entities": [str(entity) for entity in entities],
        "url": str(record["url"]) if record.get("url") else None,
        "data_origin": str(record.get("data_origin", "user_supplied")),
        **{
            key: record[key] for key in
            ("sector", "region", "publisher", "body", "dataset_timestamp", "simulation_tick")
            if key in record
        },
    }
