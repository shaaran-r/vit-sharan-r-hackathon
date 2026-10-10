import unittest
import re
from html import unescape

from src.dashboard.highlights import highlight_headline
from src.risk_engine.classification import classify_event, event_keyword_matches


class HighlightTests(unittest.TestCase):
    def test_multitoken_trigger_and_overlap_preserve_text(self):
        html, cues = highlight_headline("Severe CREDIT LOSS and default risk.")
        self.assertIn('>CREDIT LOSS</mark>', html)
        self.assertIn("credit loss (Credit Event)", cues["Event triggers"])
        self.assertEqual(cues["Negative cues"], ["severe", "loss", "default", "risk"])
        self.assertEqual(unescape(re.sub(r"<[^>]*>", "", html)), "Severe CREDIT LOSS and default risk.")
        self.assertEqual(classify_event("Severe CREDIT LOSS"), "Credit Event")

    def test_positive_and_amber_cues(self):
        html, cues = highlight_headline("A promising product launch supports strong growth.")
        self.assertIn('class="cue-positive"', html)
        self.assertIn('class="cue-trigger"', html)
        self.assertEqual(cues["Positive cues"], ["promising", "strong", "growth"])

    def test_no_substring_false_matches(self):
        _, cues = highlight_headline("Awarding a defaulted task to a growthful team.")
        self.assertFalse(any(cues.values()))
        self.assertEqual(classify_event("Company warns of loss"), "General Market")

    def test_html_is_escaped_including_inside_highlights(self):
        html, _ = highlight_headline('<script>alert("risk")</script> credit<loss & loss')
        self.assertNotIn("<script>", html)
        self.assertNotIn("credit<loss", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("credit&lt;loss</mark>", html)
        self.assertIn("&amp;", html)

    def test_punctuation_whitespace_and_priority_match_classifier(self):
        text = "Product launch follows trade-tension and INTEREST\nRATE changes."
        matches = event_keyword_matches(text)
        self.assertEqual(classify_event(text), "Geopolitical")
        self.assertTrue(all(text[start:end] for start, end, _, _ in matches))
        html, cues = highlight_headline(text)
        self.assertIn(">trade-tension</mark>", html)
        self.assertIn(">INTEREST\nRATE</mark>", html)
        self.assertEqual(len(cues["Event triggers"]), 3)

    def test_neutral_and_repeated_cues(self):
        _, neutral = highlight_headline("Scheduled quarterly update.")
        self.assertFalse(any(neutral.values()))
        html, repeated = highlight_headline("Risk and risk")
        self.assertEqual(repeated["Negative cues"], ["risk"])
        self.assertEqual(html.count("<mark "), 2)
