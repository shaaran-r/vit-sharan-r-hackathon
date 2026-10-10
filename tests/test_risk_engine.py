import os
import unittest
from datetime import date
from unittest.mock import Mock, patch

import pandas as pd
from fastapi import HTTPException
from pydantic import ValidationError

from src.api.main import PortfolioRequest, StressTestRequest, missing_portfolio, stress_test
from src.risk_engine.ingestion import LiveSourceError, fetch_live_records
from src.risk_engine.pipeline import get_signals
from src.risk_engine.sentiment import score_sentiment
from src.stress_testing.engine import parse_portfolio_csv, run_stress_test


# Artificial rows exist only in isolated tests, never in application input.
TEST_CSV = (
    "asset_id,asset_type,description,notional,duration,equity_beta,credit_duration,currency_exposure\n"
    "test-bond,bond,Test-only holding,100,2,0,2,0\n"
)


class RiskEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        from src.risk_engine import ingestion
        ingestion._live_cache.clear()
        environment = patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": ""})
        environment.start()
        self.addCleanup(environment.stop)

    def test_offline_fixture_mode_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "synthetic fixtures are disabled"):
            get_signals(mode="fixtures")

    @patch("src.risk_engine.pipeline.analyze_sentiment", return_value=(0.1, 0.8))
    @patch("src.risk_engine.pipeline.fetch_live_records")
    def test_live_pipeline_does_not_append_social_fixtures(self, fetch: Mock, sentiment: Mock) -> None:
        fetch.return_value = [{
            "source": "bbc_business_rss", "text": "Published headline",
            "event_id": "rss-1", "timestamp": "2026-10-08T08:00:00Z",
        }]
        self.assertEqual([s["source"] for s in get_signals()], ["bbc_business_rss"])

    @patch("src.risk_engine.ingestion.fetch_gdelt_records")
    @patch("src.risk_engine.ingestion.fetch_rss_records")
    def test_live_news_is_cached_without_gdelt(self, rss: Mock, gdelt: Mock) -> None:
        rss.return_value = [{"event_id": "rss-1", "source": "bbc_business_rss", "text": "Published headline"}]
        self.assertEqual(fetch_live_records(), fetch_live_records())
        self.assertEqual(rss.call_count, 2)
        gdelt.assert_not_called()

    @patch("src.risk_engine.ingestion.fetch_rss_records")
    def test_backup_provider_is_used(self, rss: Mock) -> None:
        rss.side_effect = [LiveSourceError("BBC unavailable"), [{"event_id": "cnbc-1", "source": "cnbc_business_rss"}]]
        self.assertEqual(fetch_live_records()[0]["source"], "cnbc_business_rss")

    @patch("src.risk_engine.ingestion.fetch_rss_records", side_effect=LiveSourceError("Unavailable"))
    def test_all_provider_errors_remain_explicit(self, rss: Mock) -> None:
        with self.assertRaisesRegex(LiveSourceError, "All live news sources failed"):
            fetch_live_records()

    def test_stress_test_requires_uploaded_portfolio(self) -> None:
        with self.assertRaisesRegex(ValueError, "Upload a real portfolio"):
            run_stress_test({"event_classification": "Credit Event"})

    def test_portfolio_rejects_missing_columns(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            parse_portfolio_csv("asset_id,notional\nx,100\n")

    def test_portfolio_rejects_invalid_numeric_values(self) -> None:
        for invalid in ("NaN", "inf", "-100", "invalid"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    parse_portfolio_csv(TEST_CSV.replace(",100,", f",{invalid},"))

    def test_duplicate_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            parse_portfolio_csv(TEST_CSV + TEST_CSV.splitlines()[1] + "\n")

    def test_correct_scenario_arithmetic(self) -> None:
        signal = {"event_id": "test", "event_classification": "Credit Event", "impact_score": 9}
        result = run_stress_test(signal, parse_portfolio_csv(TEST_CSV))
        self.assertEqual(result["portfolio_before"], 100)
        self.assertEqual(result["portfolio_after"], 90)
        self.assertIn("Hypothetical", result["result_type"])

    def test_api_requires_provenance_and_confirmation(self) -> None:
        with self.assertRaises(ValidationError):
            PortfolioRequest(
                csv_text=TEST_CSV, source_reference="Test only",
                valuation_date=date.today(), currency="GBP", authorized_real_data=False,
            )
        with self.assertRaises(ValidationError):
            StressTestRequest(event_classification="Credit Event", impact_score=9)

    def test_legacy_stress_route_requires_upload(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            missing_portfolio()
        self.assertEqual(raised.exception.status_code, 409)

    def test_uploaded_portfolio_currency_and_provenance_are_preserved(self) -> None:
        portfolio = PortfolioRequest(
            csv_text=TEST_CSV, source_reference="Test-only data",
            valuation_date=date.today(), currency="GBP", authorized_real_data=True,
        )
        outcome = stress_test(StressTestRequest(
            event_classification="Credit Event", impact_score=9, portfolio=portfolio,
        ))
        self.assertEqual(outcome["result"]["currency"], "GBP")
        self.assertIn("not independently verified", outcome["result"]["provenance_status"])

    def test_lexicon_is_explicitly_selectable(self) -> None:
        with patch.dict(os.environ, {"SENTIMENT_BACKEND": "lexicon"}):
            self.assertLess(score_sentiment("severe credit loss and default"), 0)


if __name__ == "__main__":
    unittest.main()
