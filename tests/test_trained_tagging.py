import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import khmereasytools as ket
from khmereasytools.compact_pos import default_model


class TrainedTaggerTests(unittest.TestCase):
    def test_grammar_role_remains_visible_across_a_corpus_tagset_difference(self):
        text = "គាត់អាចអាន។"
        rule = next(t for t in ket.khtag(text, model="rules", with_spans=True) if t.text == "អាច")
        learned = next(t for t in ket.khtag(text, with_spans=True) if t.text == "អាច")
        self.assertEqual(rule.tag, "AUX")
        self.assertEqual(learned.tag, "VERB")
        self.assertEqual(learned.role, "ability")
        self.assertIn("Role heuristic:", learned.reason)

    def test_default_recognizes_documented_grammar_and_source_positions(self):
        text = "ខ្ញុំ\u200bកំពុងអានសៀវភៅ។\r\nសិស្ស៣នាក់រៀន។"
        tokens = ket.khtag(text, with_spans=True)
        self.assertEqual([(t.text, t.tag) for t in tokens[:5]], [
            ("ខ្ញុំ", "PRON"), ("កំពុង", "AUX"), ("អាន", "VERB"), ("សៀវភៅ", "NOUN"), ("។", "PUNCT")])
        self.assertEqual(next(t.role for t in tokens if t.text == "កំពុង"), "progressive")
        self.assertEqual(next(t.role for t in tokens if t.text == "នាក់"), "classifier")
        for token in tokens:
            self.assertEqual(token.text, text[token.start:token.end])
            self.assertIn(token.tag, token.candidates)
            self.assertIn("Compact CRF predicted", token.reason)

    def test_compound_boundary_regression_improves_without_global_changes(self):
        text = "ខ្ញុំនៅផ្ទះ។"
        before = ket.khseg(text)
        self.assertEqual(ket.khtag(text), [("ខ្ញុំ", "PRON"), ("នៅ", "VERB"), ("ផ្ទះ", "NOUN"), ("។", "PUNCT")])
        self.assertIn(("នៅផ្ទះ", "X"), ket.khtag(text, model="rules"))
        self.assertEqual(ket.khseg(text), before)

    def test_unseen_word_is_marked_as_model_prediction(self):
        word = "កខគឃ"
        self.assertNotIn(word, default_model().word_counts)
        token = ket.khtag(word, custom_words=[word], with_spans=True)[0]
        self.assertEqual(token.text, word)
        self.assertNotEqual(token.tag, "X")
        self.assertIn("unseen in training", token.reason)
        self.assertFalse(hasattr(token, "confidence"))

    def test_user_override_wins_and_is_local(self):
        text = "និមលអានសៀវភៅ។"
        before = ket.khtag(text)
        tagger = ket.KhmerTagger({"និមល": "PROPN", "អាន": "NOUN"})
        tagged = tagger.tag(text, with_spans=True)
        self.assertEqual(tagged[0].tag, "PROPN")
        self.assertEqual(next(t.tag for t in tagged if t.text == "អាន"), "NOUN")
        self.assertTrue(all(t.rule == "user.lexicon" for t in tagged if t.text in ("និមល", "អាន")))
        self.assertEqual(ket.khtag(text), before)

    def test_packaged_model_hash_license_and_size(self):
        base = Path(ket.__file__).parent / "data/research"
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
        data = (base / "ket_pos_v2.json.gz").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), manifest["sha256"])
        self.assertLess(len(data), 2 * 1024 * 1024)
        self.assertEqual(manifest["license"], "CC-BY-NC-SA-4.0")
        notice = (base / "LICENSE.txt").read_text(encoding="utf-8")
        self.assertIn("Vichet Chea", notice)
        self.assertIn("Ye Kyaw Thu", notice)
        self.assertIn("NonCommercial", notice)
        self.assertEqual(default_model().metadata["training_sentences"], 9827)
        with self.assertRaises(TypeError):
            default_model().word_counts["new"] = 1

    def test_rules_mode_and_import_never_open_the_research_model(self):
        script = '''
from unittest.mock import patch
with patch("gzip.GzipFile", side_effect=AssertionError("must stay unloaded")):
 import khmereasytools as ket
 assert ket.khtag("ខ្ញុំអាន។", model="rules")[0] == ("ខ្ញុំ", "PRON")
'''
        result = subprocess.run([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))

    def test_default_needs_no_optional_packages_or_network(self):
        script = '''
import sys
from unittest.mock import patch
with patch("socket.socket", side_effect=AssertionError("offline")):
 import khmereasytools as ket
 assert ket.khtag("ខ្ញុំអាន។")[0] == ("ខ្ញុំ", "PRON")
assert not {"numpy","sklearn","pycrfsuite","khmernltk","torch","PIL"} & set(sys.modules)
'''
        result = subprocess.run([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))

    def test_local_model_path_and_validation_without_silent_fallback(self):
        path = Path(ket.__file__).parent / "data/research/ket_pos_v2.json.gz"
        self.assertEqual(ket.khtag("ខ្ញុំអាន។", model=path), ket.khtag("ខ្ញុំអាន។"))
        for model in (None, True, 10, []):
            with self.subTest(model=model), self.assertRaises(TypeError):
                ket.khtag("", model=model)
        with self.assertRaises(ValueError):
            ket.khtag("", model="")
        with self.assertRaises(OSError):
            ket.khtag("ខ្មែរ", model="nonexistent-pos-model.json.gz")

    def test_reusable_default_tagger_concurrency(self):
        tagger = ket.KhmerTagger()
        text = "សិស្ស៣នាក់កំពុងរៀន។"
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda unused: tagger.tag(text, with_spans=True), range(24)))
        self.assertTrue(all(result == results[0] for result in results))

    def test_cli_defaults_to_learned_and_accepts_rules_and_local_model(self):
        text = "ខ្ញុំនៅផ្ទះ។"
        for options in ([], ["--model", "rules"]):
            result = subprocess.run([sys.executable, "-m", "khmereasytools", "tag"] + options,
                                    input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
            report = json.loads(result.stdout.decode("utf-8"))
            expected = ket.khtag(text, model="rules" if options else "compact")
            self.assertEqual([(t["text"], t["tag"]) for t in report], expected)
        result = subprocess.run([sys.executable, "-m", "khmereasytools", "tag", "--model", "missing-model.json.gz"],
                                input=text.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b"Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
