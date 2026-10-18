import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import khmereasytools as ket


class SentenceTests(unittest.TestCase):
    def test_khmer_sentences_and_source_positions(self):
        text = "  សួស្តី។ ខ្ញុំអានសៀវភៅ៕  "
        self.assertEqual(ket.khsentences(text), ["សួស្តី។", "ខ្ញុំអានសៀវភៅ៕"])
        for span in ket.khsentences(text, with_spans=True):
            self.assertEqual(span.text, text[span.start:span.end])

    def test_decimals_links_email_abbreviations_and_initials(self):
        text = "Dr. A. Smith paid 12.50. Visit https://example.com/a?x=1. Email a.b@example.com!"
        self.assertEqual(ket.khsentences(text), [
            "Dr. A. Smith paid 12.50.", "Visit https://example.com/a?x=1.", "Email a.b@example.com!"])
        self.assertEqual(ket.khsentences("No. 12 is ready. No. We wait."),
                         ["No. 12 is ready.", "No.", "We wait."])

    def test_khmer_abbreviations_and_url_without_spaces(self):
        self.assertEqual(ket.khsentences("ឆ្នាំគ.ស. ២០២៦។ មានជាដើម។ល។ នៅទីនេះ។"),
                         ["ឆ្នាំគ.ស. ២០២៦។", "មានជាដើម។ល។ នៅទីនេះ។"])
        self.assertEqual(ket.khsentences("ចូលhttps://example.com។ បន្ទាប់។"),
                         ["ចូលhttps://example.com។", "បន្ទាប់។"])

    def test_wrapped_lines_paragraphs_and_pages(self):
        text = "first\r\nwrapped line\r\n\r\nsecond\fthird\u2029fourth"
        self.assertEqual(ket.khsentences(text), ["first\r\nwrapped line", "second", "third", "fourth"])
        self.assertEqual(ket.khsentences("one\r\ntwo"), ["one\r\ntwo"])
        self.assertEqual(ket.khsentences("one\n \ntwo"), ["one", "two"])

    def test_quotes_ellipsis_and_unterminated_tail(self):
        self.assertEqual(ket.khsentences('“Hello?!” Next... ចុងក្រោយ'),
                         ['“Hello?!”', 'Next...', 'ចុងក្រោយ'])
        self.assertEqual(ket.khsentences(""), [])
        self.assertEqual(ket.khsentences(" \r\n "), [])

    def test_randomized_source_coverage(self):
        randomizer = random.Random(928)
        alphabet = "កខា្ Hello១២.?!។៕\n\r\t😀\u200b"
        for _ in range(150):
            text = "".join(randomizer.choice(alphabet) for _ in range(randomizer.randrange(100)))
            covered = set()
            previous = 0
            for span in ket.khsentences(text, with_spans=True):
                self.assertGreaterEqual(span.start, previous)
                self.assertEqual(span.text, text[span.start:span.end])
                self.assertEqual(span.text, span.text.strip())
                covered.update(range(span.start, span.end))
                previous = span.end
            self.assertTrue(all(position in covered or char.isspace() for position, char in enumerate(text)))

    def test_long_unpunctuated_text_and_validation(self):
        text = "a" * 30000 + "."
        self.assertEqual(ket.khsentences(text), [text])
        with self.assertRaises(TypeError):
            ket.khsentences(None)
        with self.assertRaises(TypeError):
            ket.khsentences("text", with_spans="yes")


class ExtractionTests(unittest.TestCase):
    def test_source_spans_digits_and_contact_patterns(self):
        text = "ទំនាក់ទំនង០១២ ៣៤៥ ៦៧៨; A@Example.com; https://example.com/a?q=1។ តម្លៃ១,២៣៤.៥០៛"
        matches = ket.khextract(text)
        self.assertEqual([(item.kind, item.value) for item in matches], [
            ("phone", "+85512345678"), ("email", "A@example.com"),
            ("url", "https://example.com/a?q=1"), ("number", "1234.50")])
        for item in matches:
            self.assertEqual(item.text, text[item.start:item.end])

    def test_dates_are_calendar_valid_and_ambiguity_is_explicit(self):
        matches = ket.khextract("១៨/១០/២០២៦ 2026-10-18 01/02/2026 01/01/2026", kinds=["date"])
        self.assertEqual([item.value for item in matches], ["2026-10-18", "2026-10-18", None, "2026-01-01"])
        self.assertEqual(ket.khextract("01/02/2026", date_order="DMY")[0].value, "2026-02-01")
        self.assertEqual(ket.khextract("01/02/2026", date_order="MDY")[0].value, "2026-01-02")
        self.assertEqual(ket.khextract("2026-02-30 31/04/2026 0000-01-01", kinds=["date"]), [])
        self.assertEqual(ket.khextract("2024-02-29", kinds=["date"])[0].value, "2024-02-29")

    def test_dates_do_not_emit_nested_numbers(self):
        self.assertEqual(ket.khextract("2026-10-18 01/02/2026", kinds=["number"]), [])
        self.assertEqual(ket.khextract("18/10/2026", kinds=["date"], date_order="MDY"), [])

    def test_cambodian_phone_candidates_and_no_partial_long_numbers(self):
        text = "+855 12 345 678; +855 (0)12 345 678; 0123456789; 01234567890"
        phones = ket.khextract(text, kinds=["phone"])
        self.assertEqual([item.value for item in phones], ["+85512345678", "+85512345678", "+855123456789"])
        self.assertEqual(len(phones), 3)

    def test_link_trimming_balanced_brackets_and_overlap_filtering(self):
        text = "(https://example.com/a(b)). https://example.com/a.) a12@example.com"
        matches = ket.khextract(text)
        self.assertEqual([item.text for item in matches],
                         ["https://example.com/a(b)", "https://example.com/a", "a12@example.com"])
        self.assertEqual(ket.khextract(text, kinds=["number"]), [])
        long_url = "https://example.com/a" + ")" * 10000
        self.assertEqual(ket.khextract(long_url, kinds=["url"])[0].text, "https://example.com/a")

    def test_numbers_keep_precision_leading_zeros_and_terminal_punctuation(self):
        text = "តម្លៃ−០០១២.៥០, 1,234.50 and 42. A123 12,34"
        self.assertEqual([item.value for item in ket.khextract(text, kinds=["number"])],
                         ["-0012.50", "1234.50", "42"])

    def test_rejects_basic_invalid_emails(self):
        self.assertEqual(ket.khextract("a..b@example.com a@-example.com a@example-.com", kinds=["email"]), [])

    def test_validation_empty_and_kind_filter(self):
        self.assertEqual(ket.khextract(""), [])
        self.assertEqual(ket.khextract("១២", kinds=[]), [])
        self.assertEqual(ket.khextract("០០៧", kinds=(kind for kind in ["number"]))[0].value, "007")
        with self.assertRaises(TypeError):
            ket.khextract(None)
        with self.assertRaises(TypeError):
            ket.khextract("text", kinds="email")
        with self.assertRaises(ValueError):
            ket.khextract("text", kinds=["person"])
        with self.assertRaises(ValueError):
            ket.khextract("text", date_order="guess")


class ProcessingTests(unittest.TestCase):
    def test_utf8_text_pipeline_and_original_mapping(self):
        original = "\ufeffសួស្តី។\r\nលេខ ០០៧."
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "អត្ថបទ.txt"
            path.write_bytes(original.encode("utf-8"))
            report = ket.khprocess(path)
            self.assertEqual(path.read_bytes(), original.encode("utf-8"))
        self.assertEqual(report.source_type, "text")
        self.assertEqual(report.original_text, original)
        self.assertEqual(report.text, "សួស្តី។\nលេខ ០០៧.")
        self.assertIsNone(report.document)
        self.assertEqual("".join(token.text for token in report.tokens), report.text)
        self.assertIn("bom", [issue.code for issue in report.audit.issues])
        entity = report.entities[0]
        self.assertEqual(entity.value, "007")
        source = report.normalization.source_spans
        self.assertEqual(original[source[entity.start][0]:source[entity.end - 1][1]], entity.text)

    def test_unknown_text_extension_empty_input_and_literal_pdf_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes"
            path.write_text("", encoding="utf-8")
            self.assertEqual(ket.khprocess(path).text, "")
            path = Path(directory) / "notes.txt"
            path.write_text("The literal %PDF- marker is text.", encoding="utf-8")
            self.assertEqual(ket.khprocess(path).source_type, "text")

    def test_image_delegation_and_date_order(self):
        image = Path(__file__).parent / "fixtures/khmer_page.png"
        document = ket.DocumentLayout("image", 1, (), "សួស្តី។ 01/02/2026")
        with patch("khmereasytools.processing.khanalyze", return_value=document) as analyze:
            report = ket.khprocess(image, date_order="DMY", psm=6)
        self.assertIs(report.document, document)
        self.assertEqual(report.entities[0].value, "2026-02-01")
        analyze.assert_called_once_with(image, pages=None, psm=6, segment=False)

    def test_missing_binary_bad_encoding_and_text_options(self):
        with self.assertRaises(FileNotFoundError):
            ket.khprocess("/nonexistent/ket-document.txt")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            for content in (b"\0abc", b"\xff\xfe"):
                path.write_bytes(content)
                with self.assertRaises((ValueError, UnicodeError)):
                    ket.khprocess(path)
            path.write_text("text", encoding="utf-8")
            for options in ({"pages": [1]}, {"lang": "khm"}, {"date_order": "guess"}):
                with self.assertRaises(ValueError):
                    ket.khprocess(path, **options)


class DoctorTests(unittest.TestCase):
    def report(self, *, missing=(), executable="/test/tesseract", result=None):
        if result is None:
            result = subprocess.CompletedProcess([], 0, b"List of available languages (2):\neng\nkhm\n", b"")
        with patch("khmereasytools.diagnostics._available", side_effect=lambda name: name not in missing), \
                patch("platform.system", return_value="Linux"), \
                patch("shutil.which", return_value=executable), \
                patch("khmereasytools.diagnostics._run", return_value=result):
            return ket.khdoctor()

    def test_ready_configuration_and_no_key_disclosure(self):
        secret = "private-fixture-key"
        with patch.dict(os.environ, {"GOOGLE_TRANSLATE_API_KEY": secret}):
            report = self.report()
        statuses = {check.name: check.status for check in report.checks}
        self.assertEqual(statuses, dict(core="ready", ocr="ready", pdf="ready", pos="ready", translation="configured"))
        self.assertNotIn(secret, str(report))

    def test_missing_packages_are_optional_and_actionable(self):
        report = self.report(missing=("PIL", "pypdfium2", "khmernltk"))
        checks = {check.name: check for check in report.checks}
        self.assertEqual(checks["core"].status, "ready")
        self.assertEqual(checks["ocr"].status, "missing")
        self.assertIn("[ocr]", checks["pdf"].hint)
        self.assertIn("[khmernltk]", checks["pos"].hint)

    def test_missing_engine_and_language(self):
        report = self.report(executable=None)
        self.assertIn("PATH", next(check for check in report.checks if check.name == "ocr").message)
        result = subprocess.CompletedProcess([], 0, b"List of available languages (1):\neng\n", b"")
        report = self.report(result=result)
        check = next(check for check in report.checks if check.name == "ocr")
        self.assertEqual(check.status, "missing")
        self.assertIn("khm", check.message)

    def test_probe_error_and_timeout_are_reported(self):
        result = subprocess.CompletedProcess([], 1, b"", b"engine error")
        self.assertEqual(next(check for check in self.report(result=result).checks if check.name == "ocr").status, "error")
        with patch("khmereasytools.diagnostics._available", return_value=True), \
                patch("shutil.which", return_value="/test/tesseract"), \
                patch("khmereasytools.diagnostics._run", side_effect=subprocess.TimeoutExpired("tesseract", 5)):
            report = ket.khdoctor()
        self.assertEqual(next(check for check in report.checks if check.name == "ocr").status, "error")

    def test_invalid_probe_timeout(self):
        for timeout in (0, -1, True, float("inf")):
            with self.assertRaises(ValueError):
                ket.khdoctor(timeout=timeout)

    def test_does_not_import_optional_packages(self):
        code = ("import sys; from khmereasytools import khdoctor; khdoctor(); "
                "assert not {'PIL','pytesseract','pypdfium2','khmernltk','numpy','scipy','sklearn'} & set(sys.modules)")
        subprocess.run([sys.executable, "-c", code], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class DailyCLITests(unittest.TestCase):
    def cli(self, *args, data=b""):
        return subprocess.run([sys.executable, "-m", "khmereasytools"] + list(args),
                              input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_sentences_and_extraction_stdin(self):
        result = self.cli("sentences", data="សួស្តី។ បន្ទាប់។".encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([item["text"] for item in json.loads(result.stdout)], ["សួស្តី។", "បន្ទាប់។"])
        result = self.cli("extract", "--kind", "date", "--date-order", "DMY", data=b"01/02/2026")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["value"], "2026-02-01")

    def test_process_plain_text_and_optional_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_bytes("\ufeffសួស្តី។\r\n".encode())
            plain = self.cli("process", str(path))
            detailed = self.cli("process", str(path), "--json")
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertEqual(plain.stdout.decode(), "សួស្តី។\n")
        self.assertEqual(detailed.returncode, 0, detailed.stderr)
        report = json.loads(detailed.stdout)
        self.assertEqual(report["text"], "សួស្តី។\n")
        self.assertEqual(report["sentences"][0]["text"], "សួស្តី។")

    def test_doctor_default_and_required_missing_feature(self):
        with patch.dict(os.environ, {"GOOGLE_TRANSLATE_API_KEY": ""}):
            plain = self.cli("doctor")
            detailed = self.cli("doctor", "--json")
            required = self.cli("doctor", "--require", "translation")
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertIn(b"core: ready", plain.stdout)
        self.assertEqual(detailed.returncode, 0, detailed.stderr)
        self.assertEqual(json.loads(detailed.stdout)["checks"][0]["status"], "ready")
        self.assertEqual(required.returncode, 2)


if __name__ == "__main__":
    unittest.main()
