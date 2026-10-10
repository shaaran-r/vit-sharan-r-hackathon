import hashlib
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from threading import Lock
from threading import Event, Thread
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests


GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
RSS_FEED_URLS = {
    "bbc_business_rss": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "cnbc_business_rss": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
}
LIVE_CACHE_SECONDS = 60
_live_cache: dict[int, tuple[float, list[dict[str, Any]]]] = {}
_live_cache_lock = Lock()
logger = logging.getLogger(__name__)
_provider_status: dict[str, dict[str, Any]] = {}


class LiveSourceError(RuntimeError):
    pass


def fetch_gdelt_records(query: str = "finance", limit: int = 25) -> list[dict[str, Any]]:
    """Fetch recent public news article metadata from GDELT DOC 2.0."""
    if not query.strip():
        raise ValueError("GDELT query must not be empty")
    if not 1 <= limit <= 100:
        raise ValueError("GDELT limit must be between 1 and 100")

    try:
        response = requests.get(
            GDELT_API_URL,
            params={
                "query": query,
                "mode": "artlist",
                "format": "json",
                "maxrecords": limit,
                "sort": "DateDesc",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise LiveSourceError(f"GDELT news request failed: {error}") from error

    articles = payload.get("articles") if isinstance(payload, dict) else None
    if not isinstance(articles, list):
        raise LiveSourceError("GDELT response did not contain an articles list")

    records: list[dict[str, Any]] = []
    for article in articles:
        if not isinstance(article, dict):
            continue
        title = str(article.get("title") or "").strip()
        if not title:
            continue
        url = str(article.get("url") or "").strip()
        timestamp = str(article.get("seendate") or "").strip()
        if not timestamp:
            continue
        stable_key = url or f"{timestamp}:{title}"
        records.append({
            "event_id": f"gdelt-{hashlib.sha256(stable_key.encode('utf-8')).hexdigest()[:16]}",
            "source": "gdelt",
            "timestamp": timestamp,
            "text": title,
            "entities": [],
            "url": url or None,
        })
    return records


def fetch_rss_records(source: str, url: str, limit: int = 25) -> list[dict[str, Any]]:
    """Fetch public RSS headlines from a publisher feed."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "SignalAndStress/1.0 (public RSS reader)"},
            timeout=15,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError) as error:
        raise LiveSourceError(f"{source} request failed: {error}") from error

    records: list[dict[str, Any]] = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        raw_date = (item.findtext("pubDate") or "").strip()
        if not title:
            continue
        try:
            timestamp = parsedate_to_datetime(raw_date).astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            logger.warning("%s skipped a headline with invalid publication date", source)
            continue

        stable_key = link or f"{timestamp.isoformat()}:{title}"
        records.append({
            "event_id": f"{source}-{hashlib.sha256(stable_key.encode('utf-8')).hexdigest()[:16]}",
            "source": source,
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "text": title,
            "entities": [],
            "url": link or None,
        })
    if not records:
        raise LiveSourceError(f"{source} returned no usable headlines")
    return records


def fetch_live_records(query: str = "finance", limit: int = 25) -> list[dict[str, Any]]:
    """Poll both independent publishers, without depending on GDELT.

    The query argument is retained for API compatibility; RSS feeds provide
    their full business-news selection. Search is applied in the dashboard.
    """
    if not 1 <= limit <= 100:
        raise ValueError("Live news limit must be between 1 and 100")
    with _live_cache_lock:
        cached = _live_cache.get(limit)
        if cached and time.monotonic() - cached[0] < LIVE_CACHE_SECONDS:
            return [record.copy() for record in cached[1]]

        failures: list[str] = []
        combined = []
        with ThreadPoolExecutor(max_workers=len(RSS_FEED_URLS)) as pool:
            pending = {
                source: pool.submit(fetch_rss_records, source, url, limit)
                for source, url in RSS_FEED_URLS.items()
            }
            for source, future in pending.items():
                checked_at = datetime.now(timezone.utc).isoformat()
                try:
                    records = future.result()
                    if not records:
                        raise LiveSourceError(f"{source} returned no usable headlines")
                    combined.extend(records)
                    _provider_status[source] = {
                        "status": "ok", "checked_at": checked_at, "article_count": len(records),
                        "latest_publication": max(str(record.get("timestamp", "")) for record in records),
                        "message": "Publisher RSS loaded",
                    }
                except LiveSourceError as error:
                    logger.warning("Live news provider unavailable: %s", error)
                    failures.append(str(error))
                    _provider_status[source] = {
                        "status": "unavailable", "checked_at": checked_at,
                        "article_count": 0, "message": str(error),
                    }

        if combined:
            unique = {record["event_id"]: record for record in combined}
            # Stable publisher IDs avoid repeating identical feed entries within a snapshot.
            combined = sorted(unique.values(), key=lambda record: record.get("timestamp", ""), reverse=True)
            _live_cache[limit] = (time.monotonic(), combined)
            return [record.copy() for record in combined]

        details = "; ".join(failures)
        raise LiveSourceError(f"All live news sources failed: {details}")


class LiveNewsCollector:
    def __init__(self) -> None:
        self._stop = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._records: list[dict[str, Any]] = []
        self._error = "Live publisher collection is starting; retry shortly."
        self._checked_at: str | None = None

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="publisher-news-poller", daemon=True)
        self._thread.start()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=35)
            if self._thread.is_alive():
                raise RuntimeError("Publisher collector did not stop within 35 seconds")

    def refresh(self) -> None:
        try:
            records = fetch_live_records()
            error = ""
        except LiveSourceError as failure:
            records, error = [], str(failure)
            logger.warning("Continuous publisher collection failed: %s", error)
        with self._lock:
            self._records = records
            self._error = error
            self._checked_at = datetime.now(timezone.utc).isoformat()

    def _run(self) -> None:
        while not self._stop.is_set():
            self.refresh()
            if self._stop.wait(LIVE_CACHE_SECONDS):
                break

    def records(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self._records:
                raise LiveSourceError(self._error)
            return [record.copy() for record in self._records]

    def status(self) -> dict[str, Any]:
        with self._lock:
            snapshot = {
                "running": self.running, "poll_seconds": LIVE_CACHE_SECONDS,
                "last_collection": self._checked_at, "article_count": len(self._records),
                "message": self._error or "Continuous real news collection active",
                "transport": "External RSS polling; not publisher push or market-price streaming",
            }
        with _live_cache_lock:
            snapshot["providers"] = {source: dict(status) for source, status in _provider_status.items()}
        return snapshot


live_collector = LiveNewsCollector()
