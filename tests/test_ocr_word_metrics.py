import random
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    from ocr_word_metrics import aggregate, edit_counts, segmented_tokens, whitespace_tokens
    from audit_document_ocr import slow_distance
except ImportError:
    edit_counts = None


@unittest.skipIf(edit_counts is None, "Optional research dependency rapidfuzz is not installed")
class OCRWordMetricsTests(unittest.TestCase):
    def test_insertions_are_unbounded_and_empty_reference_has_no_rate(self):
        score = edit_counts(["ក"], ["ក"] * 8)
        self.assertEqual(score["insertions"], 7)
        self.assertEqual(score["error_rate"], 7)
        empty = edit_counts([], ["word"])
        self.assertEqual(empty["edits"], 1)
        self.assertIsNone(empty["error_rate"])

    def test_micro_average_and_substitution_deletion(self):
        a = edit_counts(["a", "b", "c"], ["a", "z"])
        b = edit_counts(["a"], ["a"])
        self.assertEqual(a["edits"], 2)
        self.assertEqual(aggregate([a, b])["error_rate"], 0.5)

    def test_tokenization_is_explicit_and_preserves_case_digits_and_punctuation(self):
        self.assertEqual(whitespace_tokens("ក\u200bខ\nABC ១"), ["ក", "ខ", "ABC", "១"])
        tokens = segmented_tokens("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ។ ABC ១")
        self.assertEqual("".join(tokens), "ខ្ញុំស្រឡាញ់ភាសាខ្មែរ។ABC១")
        self.assertIn("។", tokens)

    def test_minimum_token_edit_counts_match_independent_dynamic_programming(self):
        rng = random.Random(20261018)
        alphabet = ["ក", "ខ", "ab", "១", "."]
        for _ in range(100):
            ref = [rng.choice(alphabet) for _ in range(rng.randrange(20))]
            pred = [rng.choice(alphabet) for _ in range(rng.randrange(20))]
            self.assertEqual(edit_counts(ref, pred)["edits"], slow_distance(ref, pred))
