"""No corpus download: test normalized matching and partition leakage policy."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
with patch.object(sys, "path", [str(SCRIPTS)] + sys.path):
    spec = importlib.util.spec_from_file_location("ket_compact_training", str(SCRIPTS / "train_compact_tagger.py"))
    training = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(training)


class PartitionTests(unittest.TestCase):
    def test_remove_exact_text_even_when_boundaries_differ_and_group_duplicates(self):
        rows = [("train:0", [("ក", "NN"), ("ខ", "VB")]),
                ("train:1", [("គ", "NN")]), ("train:2", [("គ", "VB")]),
                ("train:3", [("ឃ", "NN")]), ("train:4", [("ង", "NN")])]
        close = [("test:0", [("កខ", "NN")])]
        opened = [("test:1", [("ឃ", "NN")])]
        alt = [("test:2", [("ង", "n")])]
        train, dev, audit = training.partition_rows(rows, close, opened, alt)
        self.assertEqual(audit["removed_test_matches"], ["train:0", "train:3", "train:4"])
        self.assertEqual(audit["removed_duplicates"], ["train:2"])
        self.assertEqual(audit["conflicting_duplicate_ids"], ["train:2"])
        self.assertEqual(train + dev, [rows[1]])

    def test_split_membership_is_stable_and_train_dev_are_disjoint(self):
        rows = [(str(i), [("ក" + str(i), "NN")]) for i in range(300)]
        a, b, _ = training.partition_rows(rows, [], [], [])
        x, y, _ = training.partition_rows(list(reversed(rows)), [], [], [])
        self.assertEqual({r[0] for r in a}, {r[0] for r in x})
        self.assertEqual({r[0] for r in b}, {r[0] for r in y})
        self.assertFalse({r[0] for r in a} & {r[0] for r in b})
        self.assertTrue(a and b)

    def test_projection_joins_markers_and_rejects_bad_alignment(self):
        self.assertEqual(training.corpus_word("សាលា_រៀន~ខ្មែរ"), "សាលារៀនខ្មែរ")
        self.assertEqual(training.corpus_word("ក\\_ខ\\~គ\u200b"), "កខគ")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "toy.word").write_text("ក ខ\n", encoding="utf-8")
            (base / "toy.tag").write_text("NN\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                training.read_pairs(base, "toy")


if __name__ == "__main__":
    unittest.main()
