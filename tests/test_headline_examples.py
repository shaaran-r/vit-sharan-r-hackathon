import os
import unittest
from unittest.mock import patch

from src.api.main import AnalyzeRequest, analyze
from src.dashboard.examples import HEADLINE_EXAMPLES


class HeadlineExampleTests(unittest.TestCase):
    @patch.dict(os.environ, {"SENTIMENT_BACKEND": "lexicon"})
    def test_all_examples_use_real_analysis_and_preserve_synthetic_label(self):
        self.assertEqual(len(HEADLINE_EXAMPLES), 6)
        for example in HEADLINE_EXAMPLES:
            with self.subTest(case=example["label"]):
                result = analyze(AnalyzeRequest(
                    text=example["text"], source="synthetic_example", data_origin="synthetic",
                    entities=[entity.strip() for entity in example["entities"].split(",")],
                ))
                self.assertEqual(result["event_classification"], example["category"])
                self.assertEqual(result["data_origin"], "synthetic")
                self.assertEqual(result["source"], "synthetic_example")
                if example["category"] in {"Geopolitical", "Macroeconomic", "Credit Event"}:
                    self.assertLess(result["sentiment_score"], 0)
                    self.assertGreaterEqual(result["impact_score"], 7)
                elif example["category"] in {"Merger/Acquisition", "Product Launch"}:
                    self.assertGreater(result["sentiment_score"], 0)
                else:
                    self.assertEqual(result["sentiment_score"], 0)

    def test_manual_input_defaults_to_user_supplied(self):
        self.assertEqual(AnalyzeRequest(text="User text").data_origin, "user_supplied")
