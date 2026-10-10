import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import simulation
from src.api.main import PortfolioRequest, SyntheticPortfolioRequest, StressTestRequest, stress_test
from src.risk_engine.ingestion import LiveSourceError
from src.risk_engine.classification import classify_event
from src.risk_engine.pipeline import get_signals
from src.stress_testing.engine import parse_portfolio_csv


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.path_patch = patch.object(simulation, "DATA_DIR", Path(cls.directory.name))
        cls.path_patch.start()
        simulation.catalogue.cache_clear()
        with contextlib.redirect_stdout(io.StringIO()):
            simulation.generate_datasets()

    @classmethod
    def tearDownClass(cls):
        simulation.catalogue.cache_clear()
        cls.path_patch.stop()
        cls.directory.cleanup()

    def test_large_corpus_has_complete_diverse_provenance(self):
        manifest, records, csv_text = simulation.catalogue()
        self.assertEqual(manifest["event_count"], 12000)
        self.assertEqual(len({r["event_id"] for r in records}), 12000)
        self.assertEqual(sum(r["source"] == "synthetic_social" for r in records), 6000)
        self.assertEqual(sum(r["source"] == "synthetic_news" for r in records), 6000)
        self.assertEqual(len({r["expected_event"] for r in records}), 6)
        self.assertTrue(all(classify_event(r["text"]) == r["expected_event"] for r in records))
        self.assertTrue(all(r["data_origin"] == "synthetic" and r["body"] and not r["url"] for r in records))
        holdings = parse_portfolio_csv(csv_text)
        self.assertEqual(len(holdings), 2400)
        self.assertEqual(holdings["entity_id"].nunique(), 240)
        self.assertEqual(set(holdings["asset_type"]), {"loan", "bond", "equity", "derivative", "cash"})
        self.assertEqual(holdings.groupby("asset_type").size().tolist(), [480] * 5)
        self.assertEqual(round(holdings["notional"].sum(), 2), manifest["baseline_value"])

    def test_replay_is_bounded_advances_six_and_is_repeatable(self):
        first = simulation.simulation_records(tick=10000)
        second = simulation.simulation_records(tick=10001)
        self.assertEqual(len(first), 120)
        self.assertEqual(first, simulation.simulation_records(tick=10000))
        self.assertEqual(len({r["event_id"] for r in second} - {r["event_id"] for r in first}), 6)
        self.assertEqual(first[6:][0]["event_id"], second[0]["event_id"])
        self.assertTrue(all("dataset_timestamp" in r for r in first))

    def test_synthetic_portfolio_cannot_be_declared_real(self):
        payload = simulation.simulation_portfolio()
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            PortfolioRequest(**payload, authorized_real_data=True)
        request = StressTestRequest(
            portfolio=payload, event_classification="Credit Event", impact_score=9,
        )
        self.assertIsInstance(request.portfolio, SyntheticPortfolioRequest)
        result = stress_test(request)["result"]
        self.assertEqual(result["data_origin"], "synthetic")
        self.assertEqual(len(result["holdings"]), 2400)
        self.assertEqual(result["portfolio_before"], simulation.simulation_status()["baseline_value"])
        self.assertLess(result["portfolio_after"], result["portfolio_before"])
        self.assertIn("credit_pnl", result["holdings"][0])

    @patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "", "SENTIMENT_BACKEND": "lexicon"})
    @patch("src.risk_engine.pipeline.fetch_live_records")
    def test_hybrid_preserves_live_news_and_labels_simulation(self, fetch):
        fetch.return_value = [{"event_id": "rss-test", "text": "Published news", "source": "bbc_business_rss"}]
        signals = get_signals(mode="hybrid")
        self.assertEqual(len(signals), 121)
        self.assertEqual(signals[0]["data_origin"], "live_publisher")
        self.assertTrue(all(s["data_origin"] == "synthetic" for s in signals[1:]))
        self.assertTrue(all(-1 <= s["sentiment_score"] <= 1 and 1 <= s["impact_score"] <= 10 for s in signals))
        self.assertTrue(any(s["impact_score"] >= 8 for s in signals))

    @patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "", "SENTIMENT_BACKEND": "lexicon"})
    @patch("src.risk_engine.pipeline.fetch_live_records", side_effect=LiveSourceError("Offline"))
    def test_hybrid_replay_survives_live_outage_without_mislabeling(self, fetch):
        self.assertTrue(all(s["data_origin"] == "synthetic" for s in get_signals(mode="hybrid")))
        with self.assertRaises(LiveSourceError):
            get_signals(mode="live")


if __name__ == "__main__":
    unittest.main()
