import random
import unittest

from khmereasytools import khseg, khseg_spans, khsyllable


class SegmentationTests(unittest.TestCase):
    def assert_lossless(self, text, tokens):
        self.assertEqual("".join(token.text for token in tokens), text)
        position = 0
        for token in tokens:
            self.assertEqual(token.start, position)
            self.assertGreater(token.end, token.start)
            self.assertEqual(token.text, text[token.start:token.end])
            position = token.end
        self.assertEqual(position, len(text))

    def test_existing_quickstart(self):
        text = "ខ្ញុំស្រឡាញ់ភាសាខ្មែរ"
        self.assertEqual([token.text for token in khseg_spans(text)], khseg(text))

    def test_mixed_text_and_boundaries(self):
        text = "😀ខ្មែរ\u200b AI ២០២៦។\r\n"
        tokens = khseg_spans(text, custom_words=["ខ្មែរ"])
        self.assert_lossless(text, tokens)
        self.assertEqual([token.kind for token in tokens], [
            "other", "word", "boundary", "whitespace", "latin", "whitespace",
            "number", "punctuation", "whitespace",
        ])

    def test_custom_word_wins_longest_match(self):
        self.assertEqual([t.text for t in khseg_spans("ខ្ញុំស្រឡាញ់", ["ខ្ញុំស្រឡាញ់"])],
                         ["ខ្ញុំស្រឡាញ់"])

    def test_unknown_does_not_swallow_later_word(self):
        tokens = khseg_spans("ឋខ្ញុំ")
        self.assertEqual([(t.text, t.kind) for t in tokens],
                         [("ឋ", "unknown_khmer"), ("ខ្ញុំ", "word")])

    def test_do_not_split_before_vowel_or_inside_coeng(self):
        for text, words in (("កា", ["ក"]), ("ក្ខ", ["ក", "ខ"]),
                            ("ក្\u200dខ", ["ខ"]), ("ក\u200cា", ["ក"])):
            tokens = khseg_spans(text, words)
            self.assertEqual(len(tokens), 1)
            self.assert_lossless(text, tokens)

    def test_custom_words_do_not_mutate_default(self):
        text = "ឋឍ"
        self.assertEqual(khseg_spans(text, [text])[0].kind, "word")
        self.assertEqual(khseg_spans(text)[0].kind, "unknown_khmer")

    def test_empty(self):
        self.assertEqual(khseg_spans(""), [])

    def test_input_validation(self):
        with self.assertRaises(TypeError):
            khseg_spans(None)
        for words in ("ខ្មែរ", [1], b"abc"):
            with self.assertRaises(TypeError):
                khseg_spans("", words)
        for words in ([""], ["   "]):
            with self.assertRaises(ValueError):
                khseg_spans("", words)

    def test_randomized_losslessness(self):
        rng = random.Random(42)
        alphabet = "កខ្ា១២abc  \r\n\u200b\u200c\u200d😀។!?"
        for _ in range(300):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(80)))
            self.assert_lossless(text, khseg_spans(text))

    def test_legacy_syllable_output_is_unchanged(self):
        # This is a compatibility test, not a claim of linguistic correctness.
        self.assertEqual(khsyllable("សាលារៀន"), ["សា", "លា", "រៀ", "ន"])


if __name__ == "__main__":
    unittest.main()
