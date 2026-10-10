import os
import unittest
from unittest.mock import Mock, patch

from requests import ConnectionError

from src.risk_engine import alpha_vantage as alpha
from src.risk_engine.ingestion import LiveSourceError
from src.risk_engine.pipeline import get_signals


class AlphaVantageTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "test-only-key"})
        environment.start()
        self.addCleanup(environment.stop)
        alpha._records = []
        alpha._checked_at = None
        alpha._status = "not_checked"
        alpha._message = "Not checked."

    @patch("src.risk_engine.alpha_vantage.requests.get")
    def test_news_mapping_and_two_hour_cache(self, get: Mock) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {
            "feed": [{
                "title": "Published test headline",
                "url": "https://example.test/article",
                "time_published": "20261008T080000",
                "ticker_sentiment": [{"ticker": "TEST"}],
            }]
        }
        get.return_value = response
        records = alpha.fetch_alpha_records()
        self.assertEqual(records[0]["source"], "alpha_vantage_news")
        self.assertEqual(records[0]["timestamp"], "2026-10-08T08:00:00Z")
        self.assertEqual(records[0]["entities"], ["TEST"])
        self.assertEqual(alpha.fetch_alpha_records(), records)
        get.assert_called_once()
        self.assertNotIn("test-only-key", str(alpha.alpha_status()))

    @patch("src.risk_engine.alpha_vantage.requests.get")
    def test_quota_error_is_explicit_and_cached(self, get: Mock) -> None:
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {"Information": "Quota exceeded for test-only-key"}
        self.assertEqual(alpha.fetch_alpha_records(), [])
        self.assertEqual(alpha.fetch_alpha_records(), [])
        get.assert_called_once()
        status = alpha.alpha_status()
        self.assertEqual(status["status"], "unavailable")
        self.assertNotIn("test-only-key", str(status))

    @patch("src.risk_engine.alpha_vantage.requests.get")
    def test_connection_error_never_exposes_authenticated_url(self, get: Mock) -> None:
        get.side_effect = ConnectionError("URL https://example.test/?apikey=test-only-key")
        alpha.fetch_alpha_records()
        self.assertNotIn("test-only-key", str(alpha.alpha_status()))

    @patch("src.risk_engine.alpha_vantage.requests.get")
    def test_unconfigured_key_never_calls_api(self, get: Mock) -> None:
        with patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": ""}):
            self.assertEqual(alpha.fetch_alpha_records(), [])
            self.assertEqual(alpha.alpha_status()["status"], "disabled")
        get.assert_not_called()

    @patch("src.risk_engine.pipeline.analyze_sentiment", return_value=(0.2, 0.8))
    @patch("src.risk_engine.pipeline.fetch_live_records")
    @patch("src.risk_engine.pipeline.fetch_alpha_records")
    def test_rss_and_alpha_are_both_used(self, fetch_alpha: Mock, rss: Mock, sentiment: Mock) -> None:
        item = {
            "text": "Published headline", "timestamp": "2026-10-08T08:00:00Z", "entities": [],
        }
        rss.return_value = [{**item, "source": "bbc_business_rss"}]
        fetch_alpha.return_value = [{**item, "source": "alpha_vantage_news"}]
        self.assertEqual(
            {s["source"] for s in get_signals()},
            {"bbc_business_rss", "alpha_vantage_news"},
        )

    @patch("src.risk_engine.pipeline.analyze_sentiment", return_value=(0.2, 0.8))
    @patch("src.risk_engine.pipeline.fetch_live_records", side_effect=LiveSourceError("RSS down"))
    @patch("src.risk_engine.pipeline.fetch_alpha_records")
    def test_alpha_works_when_rss_is_down(self, fetch_alpha: Mock, rss: Mock, sentiment: Mock) -> None:
        fetch_alpha.return_value = [{
            "text": "Published headline", "timestamp": "2026-10-08T08:00:00Z",
            "source": "alpha_vantage_news",
        }]
        self.assertEqual(get_signals()[0]["source"], "alpha_vantage_news")


if __name__ == "__main__":
    unittest.main()
