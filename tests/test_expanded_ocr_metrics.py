"""Critical metric and eligibility checks for the separate research harness."""
import math
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from evaluation_metrics import text_score
from expanded_ocr_metrics import paired_interval, polygon_bounds, stable_subset, summarize, upright_dimensions


class ExpandedMetricsTests(unittest.TestCase):
    def test_source_selection_is_order_independent(self):
        names = ["photo-" + str(i) for i in range(20)]
        self.assertEqual(stable_subset(names, 5), stable_subset(list(reversed(names)), 5))
        self.assertEqual(len(stable_subset(names + names, 5)), 5)

    def test_polygon_rounding_and_tolerance(self):
        points, bounds = polygon_bounds([-.5, 10, 10, 0], [0, 0, 8, 8], 10, 10)
        self.assertEqual(bounds, (0, 0, 10, 9))
        self.assertTrue(all(0 <= x < 10 and 0 <= y < 10 for x, y in points))

    def test_polygon_coordinates_use_upright_image_dimensions(self):
        for orientation in [1, 2, 3, 4]:
            self.assertEqual(upright_dimensions(4624, 3468, orientation), (4624, 3468))
        for orientation in [5, 6, 7, 8]:
            self.assertEqual(upright_dimensions(4624, 3468, orientation), (3468, 4624))
        with self.assertRaises(ValueError):
            upright_dimensions(4624, 3468, 9)

    def test_invalid_polygons(self):
        for xs, ys in [([0, 2], [0, 2]), ([0, math.nan, 2], [0, 1, 2]),
                       ([0, 12, 0], [0, 0, 8]), ([0, 1, 2], [0, 1, 2])]:
            with self.assertRaises(ValueError):
                polygon_bounds(xs, ys, 10, 10)

    def test_identical_systems_have_zero_paired_difference(self):
        rows = []
        for i, ref in enumerate(["abc", "abcde", "xy"]):
            score = dict(text_score(ref, ref[:-1]), seconds=.1, failed=False)
            rows.append(dict(id=str(i), source_id=str(i), group=str(i),
                             baseline=score, toolkit=dict(score)))
        interval = paired_interval(rows, replicates=100)
        self.assertEqual(interval["toolkit_minus_baseline_cer_points"], 0)
        self.assertEqual(interval["percentile_95_interval"], [0, 0])

    def test_bootstrap_clusters_repeated_crops(self):
        rows = []
        for i in range(3):
            a = dict(text_score("abcd", "abcd"), seconds=.1, failed=False)
            b = dict(text_score("abcd", "abc"), seconds=.1, failed=False)
            rows.append(dict(id=str(i), source_id="same-photo", group="same-photo", baseline=a, toolkit=b))
        result = summarize(rows)
        self.assertEqual(result["paired"]["source_groups"], 1)
        self.assertEqual(result["paired"]["toolkit_minus_baseline_cer_points"], 25)
        self.assertEqual(result["paired"]["percentile_95_interval"], [25, 25])

    def test_failed_outputs_remain_in_denominator(self):
        rows = [dict(id="a", source_id="a", group="a",
                     baseline=dict(text_score("abc", ""), seconds=.1, failed=True),
                     toolkit=dict(text_score("abc", "abc"), seconds=.1, failed=False))]
        result = summarize(rows)
        self.assertEqual(result["baseline"]["failures"], 1)
        self.assertEqual(result["baseline"]["reference_codepoints"], 3)
        self.assertEqual(result["baseline"]["compact_codepoint_cer"], 1)
        self.assertEqual(result["toolkit"]["compact_codepoint_cer"], 0)

    def test_mismatched_paired_references_fail(self):
        row = dict(group="a", baseline=dict(reference_codepoints=3, codepoint_edits=1),
                   toolkit=dict(reference_codepoints=4, codepoint_edits=1))
        with self.assertRaises(ValueError):
            paired_interval([row], replicates=2)


if __name__ == "__main__":
    unittest.main()
