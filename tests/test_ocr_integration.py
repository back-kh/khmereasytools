"""Opt-in tests against the real Tesseract engine and Khmer traineddata."""
import json
import os
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

from khmereasytools import khanalyze, khocr, ket_ocr, khocr_layout, khocr_overlay, khprocess, khdoctor


@unittest.skipUnless(os.environ.get("KET_RUN_OCR_TESTS") == "1", "Set KET_RUN_OCR_TESTS=1 for real OCR tests")
class RealKhmerOCRTests(unittest.TestCase):
    image = Path(__file__).parent / "fixtures/khmer_page.png"

    def test_real_engine_detects_khmer_and_line_geometry(self):
        page = khocr_layout(self.image, psm=6)
        truth = json.loads(self.image.with_suffix('.json').read_text(encoding="utf-8"))
        self.assertEqual((page.width, page.height), (1400, 800))
        self.assertGreater(page.audit.khmer_letter_count, 10)
        self.assertGreaterEqual(len(page.lines), 3)
        self.assertEqual(page.engine, "tesseract")
        # A synthetic rendering verifies integration/geometry, not OCR accuracy
        # on real scans. Do not require version-dependent exact recognized text.
        for expected in truth:
            left, top, width, height = expected["box"]
            region_bottom = top + height
            self.assertTrue(any(max(top, line.box.top) < min(region_bottom, line.box.bottom)
                                for line in page.lines))
        for word in page.words:
            self.assertGreaterEqual(word.box.left, 0)
            self.assertLessEqual(word.box.right, page.width)
            self.assertLessEqual(word.box.bottom, page.height)
        with tempfile.TemporaryDirectory() as directory:
            overlay = Path(directory) / "overlay.png"
            khocr_overlay(self.image, page, overlay)
            from PIL import Image
            with Image.open(overlay) as result:
                self.assertEqual(result.size, (1400, 800))

    def test_blank_and_transparent_images(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blank.png"
            Image.new("RGBA", (400, 300), (0, 0, 0, 0)).save(path)
            page = khocr_layout(path)
        self.assertEqual(page.text, "")
        self.assertEqual(page.words, ())
        self.assertIsNone(page.confidence)

    def test_missing_language_is_actionable(self):
        from khmereasytools import OCRError
        with self.assertRaisesRegex(OCRError, "language data"):
            khocr_layout(self.image, lang="not_installed_ket")

    def test_pdf_pages_and_coordinates(self):
        document = self.image.with_name("khmer_document.pdf")
        result = khanalyze(document, pages=[2, 1], dpi=144, psm=6)
        self.assertEqual(result.source_type, "pdf")
        self.assertEqual(result.page_count, 2)
        self.assertEqual([page.number for page in result.pages], [2, 1])
        self.assertEqual(result.pages[0].width_points, 700)
        self.assertEqual(result.pages[0].height_points, 400)
        self.assertEqual((result.pages[0].layout.width, result.pages[0].layout.height), (1400, 800))
        self.assertIn("\n\f\n", result.text)
        self.assertTrue(all(page.layout.audit.khmer_letter_count > 10 for page in result.pages))
        with self.assertRaises(ValueError):
            khanalyze(document, pages=[3])
        with self.assertRaises(ValueError):
            khanalyze(document, dpi=1000)

    def test_one_call_text_api_accepts_pdf(self):
        text = khocr(self.image.with_name("khmer_document.pdf"), pages=[1])
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 20)
        self.assertNotIn("error", text.lower())

    def test_one_call_text_api_accepts_image(self):
        text = khocr(self.image)
        self.assertIsInstance(text, str)
        self.assertGreater(sum("\u1780" <= char <= "\u17ff" for char in text), 10)
        self.assertNotIn("error", text.lower())

    def test_ket_ocr_image_pdf_and_missing_input(self):
        self.assertEqual(ket_ocr(self.image, psm=6), khanalyze(self.image, psm=6, segment=False).text)
        text = ket_ocr(self.image.with_name("khmer_document.pdf"), pages=[1], dpi=144, psm=6)
        self.assertGreater(sum("\u1780" <= char <= "\u17ff" for char in text), 10)
        with self.assertRaises(FileNotFoundError):
            ket_ocr(self.image.with_name("does-not-exist.png"))

    def test_auto_and_none_preserve_source_geometry_and_share_text_path(self):
        automatic = khocr_layout(self.image, segment=False)
        original = khocr_layout(self.image, preprocess="none", segment=False)
        self.assertEqual((automatic.width, automatic.height), (original.width, original.height))
        self.assertTrue(any("enlarged 2x" in message for message in automatic.warnings))
        self.assertFalse(any("enlarged" in message for message in original.warnings))
        self.assertEqual(khocr(self.image), automatic.text)
        self.assertEqual(khanalyze(self.image, segment=False).text, automatic.text)
        self.assertEqual(khocr(self.image, preprocess="none"), original.text)

    def test_daily_processing_pipeline_with_real_image_and_pdf(self):
        for path, options in ((self.image, {}), (self.image.with_name("khmer_document.pdf"), {"pages": [2], "dpi": 144})):
            with self.subTest(path=path):
                report = khprocess(path, psm=6, **options)
                self.assertGreater(report.audit.khmer_letter_count, 10)
                self.assertEqual("".join(token.text for token in report.tokens), report.text)
                self.assertTrue(report.sentences)
                self.assertEqual(report.document.text, report.original_text)
                if report.source_type == "pdf":
                    self.assertEqual(report.document.pages[0].number, 2)
        checks = {check.name: check.status for check in khdoctor().checks}
        self.assertEqual(checks["ocr"], "ready")
        self.assertEqual(checks["pdf"], "ready")
        result = subprocess.run([sys.executable, "-m", "khmereasytools", "process", str(self.image), "--json"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        detailed = json.loads(result.stdout)
        self.assertEqual(detailed["source_type"], "image")
        self.assertGreater(detailed["audit"]["khmer_letter_count"], 10)

    def test_daily_cli_defaults_to_text_and_layout_is_optional(self):
        base = [sys.executable, "-m", "khmereasytools", "ocr", str(self.image), "--psm", "6"]
        text = subprocess.run(base, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.decode()
        self.assertGreater(len(text), 20)
        self.assertFalse(text.startswith("{"))
        detailed = subprocess.run(base + ["--layout"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        result = json.loads(detailed.stdout)
        self.assertEqual(result["source_type"], "image")
        self.assertEqual(len(result["pages"][0]["layout"]["lines"]), 4)
        alias = subprocess.run([sys.executable, "-m", "khmereasytools", "ket-ocr", str(self.image), "--psm", "6"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.decode()
        self.assertEqual(alias, text)


if __name__ == "__main__":
    unittest.main()
