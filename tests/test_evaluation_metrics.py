"""Check metric arithmetic independently of model/recognition outputs."""
import importlib.util
import random
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts/evaluation_metrics.py"
SPEC = importlib.util.spec_from_file_location("ket_evaluation_metrics", str(PATH))
metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metrics)


class EvaluationMetricTests(unittest.TestCase):
    def test_known_edit_counts_and_normalization_policy(self):
        self.assertEqual(metrics.distance("kitten", "sitting"), 3)
        self.assertEqual(metrics.distance(["one", "two"], ["one", "three"]), 1)
        self.assertEqual(metrics.compact(" ក\u200bខ \n e\u0301"), "កខé")
        score = metrics.text_score("ក ខ", "ក ឃ")
        self.assertEqual(score["reference_codepoints"], 2)
        self.assertEqual(score["codepoint_edits"], 1)
        self.assertEqual(score["whitespace_unit_edits"], 1)
        result = metrics.aggregate_text([score, metrics.text_score("ក", "ក")])
        self.assertEqual(result["compact_codepoint_cer"], 1 / 3)

    def test_edit_distance_matches_independent_small_graph_search(self):
        # Breadth-first search over insert/delete/substitute neighbors, independent
        # of the dynamic-programming implementation used as a fallback.
        randomizer = random.Random(3902)
        for _ in range(30):
            a = "".join(randomizer.choice("កខ") for _ in range(randomizer.randrange(4)))
            b = "".join(randomizer.choice("កខ") for _ in range(randomizer.randrange(4)))
            seen, frontier, expected = {a}, {a}, 0
            while b not in frontier:
                following = set()
                for word in frontier:
                    for i in range(len(word) + 1):
                        for char in "កខ":
                            following.add(word[:i] + char + word[i:])
                        if i < len(word):
                            following.add(word[:i] + word[i + 1:])
                            for char in "កខ":
                                following.add(word[:i] + char + word[i + 1:])
                following -= seen
                seen.update(following)
                frontier, expected = following, expected + 1
            self.assertEqual(metrics.distance(a, b), expected)

    def test_overlap_matching_cannot_reuse_one_gold_box(self):
        gold = [(0, 0, 10, 10)]
        predicted = [(0, 0, 10, 10), (1, 0, 11, 10)]
        score = metrics.matched_boxes(gold, predicted)
        self.assertEqual((score["correct"], score["predicted"], score["gold"]), (1, 2, 1))
        self.assertEqual(score["f1"], 2 / 3)
        self.assertEqual(metrics.iou(gold[0], (20, 20, 30, 30)), 0)


if __name__ == "__main__":
    unittest.main()
