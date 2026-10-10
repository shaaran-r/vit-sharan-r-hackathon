import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from src import settings
import requests


NEWS_URL = "https://www.alphavantage.co/query"
CACHE_SECONDS = 2 * 60 * 60
_lock = Lock()
_records: list[dict[str, Any]] = []
_checked_at: float | None = None
_status = "not_checked"
_message = "Alpha Vantage has not been checked yet."
logger = logging.getLogger(__name__)


class AlphaVantageError(RuntimeError):
    pass


def _request_news(key: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            NEWS_URL,
            params={"function": "NEWS_SENTIMENT", "sort": "LATEST", "limit": 50, "apikey": key},
            timeout=15,
        )
    except requests.RequestException as error:
        # Request exceptions can contain the authenticated URL.
        raise AlphaVantageError("Alpha Vantage connection failed; check network access.") from None
    if response.status_code != 200:
        raise AlphaVantageError(f"Alpha Vantage returned HTTP {response.status_code}.")
    try:
        payload = response.json()
    except ValueError:
        raise AlphaVantageError("Alpha Vantage returned invalid JSON.") from None
    if not isinstance(payload, dict):
        raise AlphaVantageError("Alpha Vantage returned an unexpected response.")
    if "Information" in payload or "Note" in payload:
        raise AlphaVantageError("Alpha Vantage rejected the request: check quota and endpoint access.")
    if "Error Message" in payload:
        raise AlphaVantageError("Alpha Vantage rejected the request: check API key and endpoint parameters.")
    feed = payload.get("feed")
    if not isinstance(feed, list):
        raise AlphaVantageError("Alpha Vantage returned no news feed.")

    records = []
    for article in feed:
        if not isinstance(article, dict):
            continue
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        try:
            published = datetime.strptime(
                str(article.get("time_published") or ""), "%Y%m%dT%H%M%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if not title or not url:
            continue
        tickers = article.get("ticker_sentiment", [])
        entities = [
            item["ticker"] for item in tickers
            if isinstance(item, dict) and isinstance(item.get("ticker"), str)
        ] if isinstance(tickers, list) else []
        records.append({
            "event_id": "alpha-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16],
            "source": "alpha_vantage_news",
            "timestamp": published.isoformat().replace("+00:00", "Z"),
            "text": title,
            "entities": entities,
            "url": url,
        })
    if not records:
        raise AlphaVantageError("Alpha Vantage returned no valid dated news articles.")
    return records


def fetch_alpha_records() -> list[dict[str, Any]]:
    global _records, _checked_at, _status, _message
    key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    with _lock:
        if not key:
            _status, _message = "disabled", "Alpha Vantage is not configured."
            return []
        if _checked_at is not None and time.monotonic() - _checked_at < CACHE_SECONDS:
            return [dict(record, entities=list(record["entities"])) for record in _records]
        _checked_at = time.monotonic()
        try:
            _records = _request_news(key)
            _status = "ok"
            _message = f"Alpha Vantage news loaded: {len(_records)} articles. Cached for two hours."
        except AlphaVantageError as error:
            _records = []
            _status = "unavailable"
            _message = str(error) + " RSS remains available; retry after the two-hour cooldown."
            logger.warning("%s", _message)
        return [dict(record, entities=list(record["entities"])) for record in _records]


def alpha_status() -> dict[str, Any]:
    with _lock:
        configured = bool(os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip())
        return {
            "configured": configured,
            "status": _status if configured else "disabled",
            "message": _message if configured else "Alpha Vantage is not configured.",
            "article_count": len(_records) if configured else 0,
            "cache_seconds": CACHE_SECONDS,
        }
