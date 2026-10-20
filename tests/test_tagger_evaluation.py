"""Independent toy counts guard against inflated selective POS scores."""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
with patch.object(sys, "path", [str(SCRIPTS)] + sys.path):
    spec = importlib.util.spec_from_file_location("ket_tagger_evaluation", str(SCRIPTS / "evaluate_tagger.py"))
    evaluation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluation)


class TaggerEvaluationTests(unittest.TestCase):
    def test_abstentions_lower_all_token_accuracy_and_joint_f1(self):
        gold = [("ក", "n"), ("ខ", "v"), ("។", ".")]
        predicted = [("ក", "n"), ("ខ", "X"), ("។", ".")]
        result = evaluation.evaluate_rows([("toy", gold)], lambda text: predicted, lambda pairs: predicted)
        self.assertEqual(result["gold_boundaries"]["coverage"], 2 / 3)
        self.assertEqual(result["gold_boundaries"]["all_token_coarse_accuracy"], 2 / 3)
        self.assertEqual(result["gold_boundaries"]["selective_coarse_accuracy"], 1)
        self.assertEqual(result["gold_boundaries"]["lexical_tokens"], 2)
        self.assertEqual(result["gold_boundaries"]["lexical_covered"], 1)
        self.assertEqual(result["reconstructed_text"]["joint_coarse"]["f1"], 2 / 3)
        self.assertEqual(result["reconstructed_text"]["segmentation"]["f1"], 1)

    def test_boundary_errors_and_alignment_failures_are_scored(self):
        gold = [("ក", "n"), ("ខ", "v"), ("។", ".")]
        merged = [("កខ", "n"), ("។", ".")]
        result = evaluation.evaluate_rows([("toy", gold)], lambda text: merged, lambda pairs: gold)
        self.assertEqual(result["reconstructed_text"]["segmentation"]["f1"], 2 / 5)
        result = evaluation.evaluate_rows([("toy", gold)], lambda text: [("ខ", "v"), ("។", ".")], lambda pairs: gold)
        self.assertEqual(result["reconstructed_text"]["alignment_failures"], 1)
        self.assertEqual(result["reconstructed_text"]["joint_coarse"]["correct"], 0)

    def test_gold_boundary_adapter_rejects_changed_words(self):
        with self.assertRaises(ValueError):
            evaluation.evaluate_rows([("toy", [("ក", "n")])], lambda text: [], lambda pairs: [])

    def test_gold_input_keeps_whole_words_and_unicode_punctuation(self):
        from khmereasytools import TokenSpan
        result = evaluation.gold_input([("ភាសាខ្មែរ", "n"), ("៣", "1"), ("។", ".")], TokenSpan)
        self.assertEqual([token.text for token in result], ["ភាសាខ្មែរ", "៣", "។"])
        self.assertEqual([token.kind for token in result], ["word", "number", "punctuation"])
        self.assertEqual(result[-1].end, len("ភាសាខ្មែរ៣។"))


if __name__ == "__main__":
    unittest.main()
