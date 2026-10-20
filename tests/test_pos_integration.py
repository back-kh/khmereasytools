"""Opt-in checks against the installed khmer-nltk CRF models, without mocks."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor

from khmereasytools import khpos


@unittest.skipUnless(os.environ.get("KET_RUN_POS_TESTS") == "1", "Set KET_RUN_POS_TESTS=1 for real POS tests")
class RealPOSTests(unittest.TestCase):
    def test_model_returns_real_words_and_tags(self):
        tagged = khpos("ខ្ញុំស្រឡាញ់ខ្មែរ")
        self.assertIsInstance(tagged, list)
        self.assertEqual(len(tagged), 3)
        self.assertTrue(all(isinstance(word, str) and isinstance(tag, str) and tag for word, tag in tagged))
        self.assertIn(("ស្រឡាញ់", "v"), tagged)
        self.assertIn(("ខ្មែរ", "n"), tagged)
        self.assertEqual("".join(word for word, _ in tagged), "ខ្ញុំស្រឡាញ់ខ្មែរ")

    def test_empty_input_and_punctuation(self):
        self.assertEqual(khpos(""), [])
        tagged = khpos("ខ្ញុំទៅសាលារៀន។")
        self.assertIn(("ទៅ", "v"), tagged)
        self.assertIn(("។", "."), tagged)

    def test_preserves_selected_words_custom_names_and_no_whitespace_pairs(self):
        import importlib
        from khmereasytools import khseg
        text = "ខ្ញុំទៅសាលារៀន។"
        tagged = khpos(text)
        self.assertEqual([word for word, _ in tagged], khseg(text))
        self.assertTrue(all(word.strip() for word, _ in tagged))
        custom = "ខ្ញុំទៅសាលារៀន"
        self.assertEqual([word for word, _ in khpos(text, custom_words=[custom])], [custom, "។"])
        # A fresh process proves the 17.7 MB tokenizer model is never loaded.
        import subprocess
        import sys
        code = ("import importlib; from khmereasytools import khpos; khpos('ខ្ញុំទៅ។'); "
                "assert importlib.import_module('khmernltk.word_tokenize').crf_model is None")
        subprocess.run([sys.executable, "-c", code], check=True)

    def test_shared_native_model_is_safe_for_concurrent_calls(self):
        texts = ["ខ្ញុំស្រឡាញ់ភាសាខ្មែរ", "គាត់ទៅសាលារៀន។", "សិស្សអានសៀវភៅ។"] * 8
        expected = [khpos(text) for text in texts]
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(khpos, texts)), expected)


if __name__ == "__main__":
    unittest.main()
