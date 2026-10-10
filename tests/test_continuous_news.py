import unittest
from unittest.mock import Mock, patch

from src.risk_engine import ingestion
from src.risk_engine.ingestion import LiveNewsCollector, LiveSourceError, fetch_live_records, fetch_rss_records


class ContinuousNewsTests(unittest.TestCase):
    def setUp(self):
        ingestion._live_cache.clear()
        ingestion._provider_status.clear()

    @patch("src.risk_engine.ingestion.fetch_rss_records")
    def test_two_publishers_and_duplicates(self, fetch):
        def records(source, url, limit):
            item = {"event_id": source, "source": source, "timestamp": "2026-10-09T00:00:00Z"}
            return [item, dict(item)]
        fetch.side_effect = records
        self.assertEqual({r["source"] for r in fetch_live_records()}, set(ingestion.RSS_FEED_URLS))
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(len(fetch_live_records()), 2)
        self.assertTrue(all(item["status"] == "ok" for item in ingestion._provider_status.values()))

    @patch("src.risk_engine.ingestion.fetch_live_records")
    def test_collector_replaces_snapshot_and_surfaces_outage(self, fetch):
        collector = LiveNewsCollector()
        fetch.return_value = [{"event_id": "first"}]
        collector.refresh()
        self.assertEqual(collector.records(), [{"event_id": "first"}])
        copy = collector.records()
        copy[0]["event_id"] = "mutated"
        self.assertEqual(collector.records()[0]["event_id"], "first")
        fetch.return_value = [{"event_id": "second"}]
        collector.refresh()
        self.assertEqual(collector.records(), [{"event_id": "second"}])
        fetch.side_effect = LiveSourceError("Publishers unavailable")
        collector.refresh()
        with self.assertRaisesRegex(LiveSourceError, "Publishers unavailable"):
            collector.records()
        self.assertEqual(collector.status()["article_count"], 0)

    @patch("src.risk_engine.ingestion.fetch_live_records", return_value=[{"event_id": "fresh"}])
    def test_worker_collects_without_dashboard_and_stops(self, fetch):
        from threading import Event
        collected = Event()
        def records():
            collected.set()
            return [{"event_id": "fresh"}]
        fetch.side_effect = records
        collector = LiveNewsCollector()
        collector.start()
        try:
            self.assertTrue(collected.wait(3))
            self.assertTrue(collector.running)
        finally:
            collector.stop()
        self.assertFalse(collector.running)

    @patch("src.risk_engine.ingestion.requests.get")
    def test_invalid_dates_are_not_presented_as_current_news(self, get):
        get.return_value = Mock(content=b"""
            <rss><channel>
              <item><title>Undated</title><pubDate>invalid</pubDate></item>
              <item><title>Dated</title><pubDate>Fri, 09 Oct 2026 00:00:00 GMT</pubDate></item>
            </channel></rss>
        """)
        records = fetch_rss_records("test", "https://example.test")
        self.assertEqual([r["text"] for r in records], ["Dated"])
