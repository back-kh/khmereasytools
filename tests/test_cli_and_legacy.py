import builtins
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import khmereasytools as ket
from khmereasytools.tools import longest_match_segmenter


class LegacyTests(unittest.TestCase):
    def test_segmentation(self):
        self.assertEqual(ket.khseg("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ"), ["ខ្ញុំ", "ស្រឡាញ់", "ភាសាខ្មែរ"])
        self.assertEqual(ket.khseg("  Hello\u200b world.  "), ["Hello", "world", "."])
        self.assertEqual(ket.khseg(""), [])

    def test_longest_match(self):
        self.assertEqual(longest_match_segmenter("abc ab", {"a", "ab", "abc"}), ["abc", "ab"])
        self.assertEqual(longest_match_segmenter("abc", set()), ["abc"])

    def test_stop_words(self):
        self.assertEqual(ket.khfilter("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ", {"ខ្ញុំ"}), "ស្រឡាញ់ ភាសាខ្មែរ")
        self.assertEqual(ket.khfilter("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ", (word for word in ["", "ខ្ញុំ"])),
                         "ស្រឡាញ់ ភាសាខ្មែរ")
        words = ket.get_default_stop_words()
        self.assertEqual(len(words), 379)
        words.clear()
        self.assertEqual(len(ket.get_default_stop_words()), 379)
        self.assertEqual(ket.khfilter("ឋខ្ញុំ", {"ខ្ញុំ"}, dictionary="legacy", strategy="legacy"), "ឋខ្ញុំ")

    def test_presence(self):
        self.assertTrue(ket.is_khmer("Hello ខ្មែរ"))
        self.assertFalse(ket.is_khmer("Hello"))

    def test_load_stop_words_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "stop-words.csv")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write("ខ្ញុំ,pronoun\n ដែល ,other\n\nខ្ញុំ,duplicate\n")
            self.assertEqual(ket.load_stop_words_from_file(path), {"ខ្ញុំ", "ដែល"})

    def test_missing_stop_word_file_retains_legacy_behavior(self):
        import io
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(ket.load_stop_words_from_file("/nonexistent/ket-stop-words.csv"), set())
        self.assertIn("not found", output.getvalue())

    def test_core_does_not_import_optional_dependencies(self):
        code = "import sys, khmereasytools; assert not {'khmernltk', 'pytesseract', 'PIL', 'pypdfium2', 'numpy', 'cv2'} & set(sys.modules)"
        subprocess.run([sys.executable, "-c", code], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_missing_extras_actionable_error(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name in ("khmernltk", "pytesseract", "PIL"):
                raise ImportError("intentionally unavailable")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded_import):
            with self.assertRaisesRegex(ImportError, r"khmereasytools\[khmernltk\]"):
                ket.khpos("ខ្ញុំ")
            with self.assertRaisesRegex(ImportError, r"khmereasytools\[ocr\]"):
                ket.khocr("missing.png")

    def test_pos_uses_chosen_words_without_retokenization(self):
        fake = types.ModuleType("khmernltk")
        backend = types.ModuleType("khmernltk.pos_tag")
        backend.crf_model = None
        backend.model_path = "fixture"
        backend.create_word_features = lambda words: [{"word": word} for word in words]
        calls = []

        class Model:
            def predict(self, sentences):
                calls.append(sentences)
                return [["TEST"] * len(sentences[0])]

        backend.load_model = lambda _: Model()
        with patch.dict(sys.modules, {"khmernltk": fake, "khmernltk.pos_tag": backend}):
            self.assertEqual(ket.khpos("ខ្ញុំស្រឡាញ់"), [("ខ្ញុំ", "TEST"), ("ស្រឡាញ់", "TEST")])
            self.assertEqual(calls, [[[{"word": "ខ្ញុំ"}, {"word": "ស្រឡាញ់"}]]])

    def test_pos_empty_and_invalid_input_do_not_load_models(self):
        with patch("khmereasytools.pos._tag_words", side_effect=AssertionError("No model load")):
            self.assertEqual(ket.khpos(" \n\t"), [])
            with self.assertRaises(TypeError):
                ket.khpos(None)


class CLITests(unittest.TestCase):
    def run_cli(self, *args, data=b""):
        return subprocess.run([sys.executable, "-m", "khmereasytools"] + list(args),
                              input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_audit_json(self):
        result = self.run_cli("audit", data="កាា".encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["issues"][0]["code"], "repeated_khmer_mark")

    def test_normalize_report(self):
        result = self.run_cli("normalize", "--digits", "ascii", data="\ufeff១\r\n".encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["text"], "1\n")
        self.assertEqual(report["source_spans"], [[1, 2], [2, 4]])
        self.assertEqual(report["edits"][0]["reason"], "leading_bom")

    def test_file_newlines_are_not_translated_before_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "source.txt")
            with open(path, "wb") as handle:
                handle.write(b"a\r\nb")
            result = self.run_cli("normalize", path)
        self.assertEqual(json.loads(result.stdout)["source_spans"], [[0, 1], [1, 3], [3, 4]])

    def test_text_only_has_no_extra_newline(self):
        result = self.run_cli("normalize", "--text-only", "--digits", "ascii", data="១".encode())
        self.assertEqual(result.stdout, b"1")

    def test_digit_translation(self):
        result = self.run_cli("digits", "--target", "khmer", data=b"007")
        self.assertEqual(result.stdout.decode(), "០០៧")

    def test_custom_word_cli(self):
        result = self.run_cli("segment", "--word", "ឋឍ", data="ឋឍ".encode())
        self.assertEqual(json.loads(result.stdout), [{"text": "ឋឍ", "start": 0, "end": 2, "kind": "word"}])

    def test_bad_utf8_and_missing_file(self):
        for result in (self.run_cli("audit", data=b"\xff"), self.run_cli("audit", "/nonexistent/khmer.txt")):
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"khmereasytools:", result.stderr)
            self.assertNotIn(b"Traceback", result.stderr)

    def test_version(self):
        result = self.run_cli("--version")
        self.assertEqual(result.stdout.decode().strip(), ket.__version__)

    def test_search_files(self):
        with tempfile.TemporaryDirectory() as directory:
            first = os.path.join(directory, "សៀវភៅ.txt")
            second = os.path.join(directory, "other.txt")
            for path, text in ((first, "សិស្សអានសៀវភៅ។"), (second, "cat")):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
            result = self.run_cli("search", "សៀវភៅ", first, second)
        self.assertEqual(result.returncode, 0, result.stderr)
        hits = json.loads(result.stdout)
        self.assertEqual(hits[0]["document_id"], first)
        self.assertEqual(hits[0]["text"], "សិស្សអានសៀវភៅ។")

    def test_translate_missing_key_is_actionable(self):
        with patch.dict(os.environ, {"GOOGLE_TRANSLATE_API_KEY": ""}):
            result = self.run_cli("translate", data="សួស្តី".encode())
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"GOOGLE_TRANSLATE_API_KEY", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
