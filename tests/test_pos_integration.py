"""Opt-in checks against the installed khmer-nltk CRF models, without mocks."""
import os
import unittest

from khmereasytools import khpos


@unittest.skipUnless(os.environ.get("KET_RUN_POS_TESTS") == "1", "Set KET_RUN_POS_TESTS=1 for real POS tests")
class RealPOSTests(unittest.TestCase):
    def test_model_returns_real_words_and_tags(self):
        tagged = khpos("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ")
        self.assertIsInstance(tagged, list)
        self.assertGreaterEqual(len(tagged), 4)
        self.assertTrue(all(isinstance(word, str) and isinstance(tag, str) and tag for word, tag in tagged))
        self.assertIn(("ស្រឡាញ់", "v"), tagged)
        self.assertIn(("ខ្មែរ", "n"), tagged)
        self.assertEqual("".join(word for word, _ in tagged).replace(" ", ""), "ខ្ញុំស្រឡាញ់ភាសាខ្មែរ")

    def test_empty_input_and_punctuation(self):
        self.assertEqual(khpos(""), [])
        tagged = khpos("ខ្ញុំទៅសាលារៀន។")
        self.assertIn(("ទៅ", "v"), tagged)
        self.assertIn(("។", "."), tagged)


if __name__ == "__main__":
    unittest.main()
