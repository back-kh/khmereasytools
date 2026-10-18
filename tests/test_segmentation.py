import random
import unittest
import hashlib
import json
from pathlib import Path

from khmereasytools import get_khmer_dictionary, khseg, khseg_spans, khsyllable


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
        tokens = khseg_spans("ឋខ្ញុំ", dictionary="legacy")
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
        self.assertEqual(khseg_spans(text, dictionary="legacy")[0].kind, "unknown_khmer")

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

    def test_expanded_dictionary_provenance_and_coverage(self):
        import khmereasytools
        directory = Path(khmereasytools.__file__).parent / "data"
        manifest = json.loads((directory / "dictionary_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(get_khmer_dictionary()), manifest["combined_entries"])
        self.assertGreater(len(get_khmer_dictionary()), 80000)
        self.assertEqual(hashlib.sha256((directory / "khmer_words.txt").read_bytes()).hexdigest(),
                         manifest["output_sha256"])
        self.assertEqual(len(get_khmer_dictionary("legacy")), 213)
        self.assertIn("Unicode", (directory / "UNICODE-LICENSE.txt").read_text(encoding="utf-8"))

    def test_dictionary_copies_are_independent(self):
        words = get_khmer_dictionary()
        words.clear()
        self.assertGreater(len(get_khmer_dictionary()), 80000)

    def test_domain_words_beyond_old_lexicon(self):
        self.assertEqual(khseg("បច្ចេកវិទ្យាព័ត៌មាន"), ["បច្ចេកវិទ្យា", "ព័ត៌មាន"])
        self.assertEqual(khseg("ព្រះរាជាណាចក្រកម្ពុជា"), ["ព្រះរាជាណាចក្រ", "កម្ពុជា"])

    def test_global_coverage_avoids_greedy_dead_end(self):
        words = {"កខគ", "កខ", "គឃ"}
        greedy = khseg_spans("កខគឃ", dictionary=words, strategy="longest")
        coverage = khseg_spans("កខគឃ", dictionary=words)
        self.assertEqual([token.text for token in greedy], ["កខគ", "ឃ"])
        self.assertEqual([token.text for token in coverage], ["កខ", "គឃ"])
        self.assertTrue(all(token.kind == "word" for token in coverage))

    def test_global_score_agrees_with_exhaustive_search(self):
        rng = random.Random(837)

        def score(pieces):
            unknown, count, previous_unknown = 0, 0, False
            for word, is_unknown in pieces:
                unknown += len(word) if is_unknown else 0
                count += int(not (is_unknown and previous_unknown))
                previous_unknown = is_unknown
            return unknown, count

        def paths(text, words):
            if not text:
                yield []
                return
            candidates = [(word, False) for word in words if text.startswith(word)] + [(text[0], True)]
            for word, unknown in candidates:
                for suffix in paths(text[len(word):], words):
                    yield [(word, unknown)] + suffix

        for _ in range(80):
            text = "".join(rng.choice("កខគ") for _ in range(rng.randrange(1, 7)))
            words = {"".join(rng.choice("កខគ") for _ in range(rng.randrange(1, 4))) for _ in range(8)}
            result = khseg_spans(text, dictionary=words)
            actual = score([(token.text, token.kind == "unknown_khmer") for token in result])
            expected = min(score(path) for path in paths(text, words))
            self.assertEqual(actual, expected)

    def test_long_mark_and_joiner_runs_are_lossless(self):
        for text in ("ក" + "ា" * 10000, "ក្" + "\u200d" * 10000 + "ខ"):
            self.assert_lossless(text, khseg_spans(text, dictionary=[]))

    def test_legacy_mode_retains_original_unknown_behavior(self):
        self.assertEqual(khseg("ឋខ្ញុំ", dictionary="legacy", strategy="legacy"), ["ឋខ្ញុំ"])
        self.assertEqual(khseg("  Hello\u200b world.  ", dictionary="legacy", strategy="legacy"),
                         ["Hello", "world", "."])

    def test_mode_validation(self):
        for options in ({"dictionary": "unknown"}, {"strategy": "magic"}):
            with self.assertRaises(ValueError):
                khseg_spans("text", **options)


if __name__ == "__main__":
    unittest.main()
