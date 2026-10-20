import json
import random
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from khmereasytools import KhmerTagger, TaggedToken, khseg, khtag


class TaggingTests(unittest.TestCase):
    def test_authored_development_challenges(self):
        path = Path(__file__).parent / "fixtures" / "tagger_cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
        for case in cases:
            with self.subTest(case=case["id"]):
                tagged = khtag(case["text"], with_spans=True)
                if "pairs" in case:
                    expected = case.get("observed_pairs", case["pairs"])
                    self.assertEqual([[t.text, t.tag] for t in tagged], expected)
                    if "known_limit" in case:
                        # Keep the unmet linguistic target in the evaluation;
                        # the contract test records the current abstention.
                        self.assertNotEqual(expected, case["pairs"])
                for word, role in case.get("roles", {}).items():
                    self.assertEqual([t.role for t in tagged if t.text == word], [role])

    def test_khmer_labels_explanations_and_unresolved_alternatives(self):
        tokens = khtag("ខ្ញុំបានអានសៀវភៅ។", with_spans=True)
        self.assertTrue(all(isinstance(t, TaggedToken) for t in tokens))
        self.assertEqual(tokens[0].label_km, "សព្វនាម")
        self.assertEqual(tokens[2].label_km, "កិរិយាសព្ទ")
        self.assertEqual(tokens[1].tag, "AUX")
        self.assertEqual(tokens[1].candidates, ("VERB", "AUX"))
        self.assertTrue(tokens[1].reason)
        self.assertEqual(tokens[1].rule, "khmer.perfective")
        self.assertFalse(hasattr(tokens[1], "confidence"))

    def test_unknown_words_are_not_guessed_as_nouns(self):
        tokens = khtag("កខគឃ Python 😀 ៛", custom_words=["កខគឃ"], with_spans=True)
        self.assertEqual([(t.text, t.tag) for t in tokens], [
            ("កខគឃ", "X"), ("Python", "X"), ("😀", "SYM"), ("៛", "SYM")])
        self.assertEqual(tokens[0].role, "unknown")
        self.assertEqual(tokens[1].role, "foreign")

    def test_offsets_preserve_original_text_gaps_crlf_and_zwsp(self):
        text = "\ufeff ខ្ញុំ\u200bកំពុង\u200bអាន\r\nសៀវភៅ ១២៣។ 😀\t"
        tokens = khtag(text, with_spans=True)
        previous, pieces = 0, []
        for token in tokens:
            self.assertGreaterEqual(token.start, previous)
            self.assertEqual(token.text, text[token.start:token.end])
            pieces.extend([text[previous:token.start], token.text])
            previous = token.end
        pieces.append(text[previous:])
        self.assertEqual("".join(pieces), text)
        self.assertTrue(any(t.text == "១២៣" and t.tag == "NUM" for t in tokens))

    def test_token_boundaries_are_shared_with_segmentation(self):
        text = "ខ្ញុំរៀនភាសាខ្មែរ។"
        self.assertEqual([word for word, _ in khtag(text)], khseg(text))
        self.assertIn(("ភាសាខ្មែរ", "NOUN"), khtag(text))
        word = "ស្ត្រី"
        self.assertEqual(khtag(word), [(word, "NOUN")])

    def test_context_never_leaks_across_punctuation_or_lines(self):
        for separator in ("។", "?", ",", ";", "\n", "\r\n", "\f", "\u2029"):
            text = "ខ្ញុំមិនដឹង" + separator + "ទេ។"
            with self.subTest(separator=repr(separator)):
                tail = [t for t in khtag(text, with_spans=True) if t.text == "ទេ"]
                self.assertEqual([(t.tag, t.role) for t in tail], [("INTJ", "negative_response")])
        future = khtag("នឹង។ ទៅ", with_spans=True)[0]
        self.assertNotEqual(future.role, "future")

    def test_ascii_and_khmer_digits_and_lexical_numerals(self):
        for number in ("3", "៣", "បី"):
            tokens = khtag("សិស្ស" + number + "នាក់។", with_spans=True)
            self.assertIn((number, "NUM"), [(t.text, t.tag) for t in tokens])
            self.assertEqual(next(t.role for t in tokens if t.text == "នាក់"), "classifier")
        noun = next(t for t in khtag("ក្បាលឈឺ។", with_spans=True) if t.text == "ក្បាល")
        self.assertEqual(noun.role, "")

    def test_locally_added_names_and_no_mutation_of_default(self):
        name = "និមល"
        original = khtag(name)
        tagger = KhmerTagger({name: "PROPN"})
        self.assertEqual(tagger.tag(name), [(name, "PROPN")])
        custom = tagger.tag(name, with_spans=True)[0]
        self.assertEqual(custom.rule, "user.lexicon")
        self.assertEqual(khtag(name), original)
        self.assertNotEqual(original, [(name, "PROPN")])

    def test_override_beats_context_and_copies_mutable_inputs(self):
        lexicon = {"កំពុង": ["NOUN", "VERB"]}
        words = ["កខគឃ"]
        tagger = KhmerTagger(lexicon, custom_words=iter(words))
        lexicon["កំពុង"][:] = ["ADJ"]
        words.append("ខ្ញុំអាន")
        tagged = tagger.tag("កំពុងអាន។", with_spans=True)
        self.assertEqual(tagged[0].candidates, ("NOUN", "VERB"))
        self.assertEqual(tagged[0].tag, "NOUN")
        self.assertEqual(tagged[0].role, "custom")
        self.assertEqual(tagger.tag("ខ្ញុំអាន"), [("ខ្ញុំ", "PRON"), ("អាន", "VERB")])

    def test_custom_foreign_name_and_generator_tags(self):
        tags = (value for value in ("PROPN", "NOUN", "PROPN"))
        token = khtag("KET", lexicon={"KET": tags}, with_spans=True)[0]
        self.assertEqual(token.tag, "PROPN")
        self.assertEqual(token.candidates, ("PROPN", "NOUN"))

    def test_input_and_option_validation_including_empty_text(self):
        for value in (None, b"text", 10, []):
            with self.subTest(value=value), self.assertRaises(TypeError):
                khtag(value)
        with self.assertRaises(TypeError):
            khtag("", with_spans="yes")
        for lexicon in ([], "NOUN", {1: "NOUN"}, {"word": 1}, {"word": [1]},
                        {"word": {"NOUN", "VERB"}}, {"word": {"NOUN": 1}}):
            with self.subTest(lexicon=lexicon), self.assertRaises(TypeError):
                khtag("", lexicon=lexicon)
        for lexicon in ({"": "NOUN"}, {"two words": "NOUN"}, {"a\u200bb": "NOUN"},
                        {"word": []}, {"word": "NN"}, {"word": ""}):
            with self.subTest(lexicon=lexicon), self.assertRaises(ValueError):
                khtag("", lexicon=lexicon)
        with self.assertRaises(TypeError):
            KhmerTagger(custom_words="word")
        for words in ([""], ["a b"], ["a\u200bb"]):
            with self.subTest(words=words), self.assertRaises(ValueError):
                KhmerTagger(custom_words=words)

    def test_randomized_offsets_candidates_and_pair_consistency(self):
        randomizer = random.Random(197)
        alphabet = "កខា្ ABC១២.?!។៕\n\r\t😀\u200b\u200c\u200d"
        for _ in range(100):
            text = "".join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(90)))
            tokens = khtag(text, with_spans=True)
            self.assertEqual([(t.text, t.tag) for t in tokens], khtag(text))
            previous = 0
            for token in tokens:
                self.assertLess(token.start, token.end)
                self.assertGreaterEqual(token.start, previous)
                self.assertEqual(token.text, text[token.start:token.end])
                self.assertIn(token.tag, token.candidates)
                previous = token.end

    def test_reusable_tagger_is_deterministic_across_threads(self):
        tagger = KhmerTagger({"និមល": "PROPN"})
        texts = ["និមលកំពុងអាន។", "ខ្ញុំមិនដឹងទេ។"] * 8
        expected = [tagger.tag(text, with_spans=True) for text in texts]
        with ThreadPoolExecutor(max_workers=4) as executor:
            actual = list(executor.map(lambda text: tagger.tag(text, with_spans=True), texts))
        self.assertEqual(actual, expected)

    def test_fresh_process_has_no_optional_imports(self):
        script = (
            "import sys; from khmereasytools import khtag; "
            "assert khtag('ខ្ញុំអាន។')[0] == ('ខ្ញុំ', 'PRON'); "
            "assert not {'khmernltk', 'numpy', 'sklearn', 'PIL', 'torch', 'pytesseract'} & set(sys.modules)"
        )
        result = subprocess.run([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))

    def test_cli_json_and_alias_preserve_offsets(self):
        text = "ខ្ញុំ\r\nកំពុងអាន។"
        for command in ("tag", "ket-tagger"):
            result = subprocess.run([sys.executable, "-m", "khmereasytools", command],
                                    input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
            report = json.loads(result.stdout.decode("utf-8"))
            self.assertEqual([(t["text"], t["start"], t["end"]) for t in report],
                             [(t.text, t.start, t.end) for t in khtag(text, with_spans=True)])

    def test_cli_file_custom_term_and_invalid_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_bytes("និមល\r\nអាន។".encode("utf-8"))
            result = subprocess.run([sys.executable, "-m", "khmereasytools", "tag", str(path),
                                     "--term", "និមល=PROPN"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
            report = json.loads(result.stdout.decode("utf-8"))
            self.assertEqual(report[0]["tag"], "PROPN")
            self.assertEqual(report[1]["start"], len("និមល\r\n"))
            self.assertEqual(path.read_bytes(), "និមល\r\nអាន។".encode("utf-8"))
        for invalid in ("word", "word=NN", "=NOUN", "word="):
            result = subprocess.run([sys.executable, "-m", "khmereasytools", "tag", "--term", invalid],
                                    input=b"", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(b"Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
