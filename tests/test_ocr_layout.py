import math
import unittest
from unittest.mock import patch

from khmereasytools import khlayout, khocr_layout, khocr_overlay


def data_for(rows):
    """Rows: text, confidence, x, y, width, height, block, paragraph, line."""
    keys = ("text", "conf", "left", "top", "width", "height", "block_num", "par_num", "line_num")
    data = {key: [row[index] for row in rows] for index, key in enumerate(keys)}
    data["level"] = [5] * len(rows)
    data["page_num"] = [1] * len(rows)
    return data


class LayoutTests(unittest.TestCase):
    def test_word_boxes_confidence_and_offsets(self):
        data = data_for([("កា", 80, 10, 10, 20, 20, 1, 1, 1),
                         ("ABC", 20, 40, 10, 30, 20, 1, 1, 1),
                         ("ខ្មែរ", 90, 10, 60, 60, 30, 1, 1, 2)])
        page = khlayout(data, 200, 120)
        self.assertEqual(page.text, "កា ABC\nខ្មែរ")
        self.assertEqual(page.lines[0].confidence, 44)
        self.assertEqual(page.lines[0].box, (10, 10, 60, 20))
        self.assertEqual(page.blocks[0].line_indices, (0, 1))
        self.assertEqual(page.columns[0].line_indices, (0, 1))
        for line in page.lines:
            self.assertEqual(page.text[line.start:line.end], line.text)
            self.assertEqual("".join(token.text for token in line.tokens), line.text)
            for token in line.tokens:
                self.assertEqual(page.text[token.start:token.end], token.text)

    def test_column_order_respects_spanning_header_and_footer(self):
        rows = [("Header", 90, 20, 10, 960, 30, 1, 1, 1),
                ("Left1", 90, 40, 100, 300, 20, 2, 1, 1),
                ("Right1", 90, 600, 100, 300, 20, 3, 1, 1),
                ("Left2", 90, 40, 160, 300, 20, 2, 1, 2),
                ("Right2", 90, 600, 160, 300, 20, 3, 1, 2),
                ("Footer", 90, 20, 300, 960, 30, 4, 1, 1)]
        engine = khlayout(data_for(rows), 1000, 400)
        columns = khlayout(data_for(rows), 1000, 400, reading_order="columns")
        self.assertEqual(engine.text, "Header\nLeft1\nRight1\nLeft2\nRight2\nFooter")
        self.assertEqual(columns.text, "Header\nLeft1\nLeft2\nRight1\nRight2\nFooter")
        self.assertEqual(len(columns.columns), 2)
        self.assertEqual([line.column for line in columns.lines], [None, 0, 0, 1, 1, None])
        self.assertEqual(columns.columns[0].line_indices, (1, 2))
        self.assertEqual(columns.columns[1].line_indices, (3, 4))

    def test_blank_page(self):
        page = khlayout(data_for([]), 100, 100)
        self.assertEqual(page.text, "")
        self.assertEqual(page.words, ())
        self.assertEqual(page.lines, ())
        self.assertEqual(page.blocks, ())
        self.assertEqual(page.columns, ())
        self.assertIsNone(page.confidence)
        self.assertEqual(page.audit.character_count, 0)

    def test_filter_reports_excluded_words(self):
        rows = [("កា", 90, 0, 0, 10, 10, 1, 1, 1),
                ("ខ", 5, 20, 0, 10, 10, 1, 1, 1),
                ("គ", -1, 40, 0, 10, 10, 1, 1, 1)]
        page = khlayout(data_for(rows), 100, 100, min_confidence=50)
        self.assertEqual(page.text, "កា")
        self.assertEqual(page.filtered_word_count, 2)
        self.assertIn("2", page.warnings[-1])

    def test_page_audit_is_on_reconstructed_text(self):
        page = khlayout(data_for([("កាា", 70, 0, 0, 20, 20, 1, 1, 1)]), 100, 100)
        issue = page.audit.issues[0]
        self.assertEqual(issue.code, "repeated_khmer_mark")
        self.assertEqual(page.text[issue.start:issue.end], issue.text)

    def test_disable_segmentation(self):
        page = khlayout(data_for([("ខ្មែរ", 90, 0, 0, 40, 20, 1, 1, 1)]), 100, 100, segment=False)
        self.assertEqual(page.lines[0].tokens, ())

    def test_multiple_pages_rejected(self):
        data = data_for([("A", 90, 0, 0, 20, 20, 1, 1, 1),
                         ("B", 90, 0, 0, 20, 20, 1, 1, 1)])
        data["page_num"][1] = 2
        with self.assertRaisesRegex(ValueError, "one page"):
            khlayout(data, 100, 100)
        data["conf"][1] = -1
        with self.assertRaisesRegex(ValueError, "one page"):
            khlayout(data, 100, 100)

    def test_invalid_data_and_nonfinite_geometry(self):
        with self.assertRaises(ValueError):
            khlayout({}, 100, 100)
        data = data_for([("A", 90, 0, 0, 20, 20, 1, 1, 1)])
        data["text"].append("B")
        with self.assertRaises(ValueError):
            khlayout(data, 100, 100)
        for field, value in (("left", -1), ("left", 95), ("width", 0),
                             ("top", math.inf), ("conf", math.nan), ("conf", 101)):
            data = data_for([("A", 90, 0, 0, 20, 20, 1, 1, 1)])
            data[field][0] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                khlayout(data, 100, 100)

    def test_options_validated(self):
        for options in ({"min_confidence": -1}, {"min_confidence": math.inf}, {"reading_order": "guess"}):
            with self.assertRaises(ValueError):
                khlayout(data_for([]), 100, 100, **options)
        for width in (0, -1, True, math.nan):
            with self.assertRaises(ValueError):
                khlayout(data_for([]), width, 100)


class OCRValidationTests(unittest.TestCase):
    def test_invalid_options_fail_before_optional_imports(self):
        for options in ({"psm": 0}, {"psm": 2}, {"psm": 14}, {"psm": 6.5},
                        {"timeout": 0}, {"timeout": math.inf}, {"frame": -1},
                        {"preprocess": "magic"}, {"lang": "khm++eng"},
                        {"reading_order": "guess"}, {"min_confidence": 101}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                khocr_layout("missing.png", **options)

    def test_overlay_never_overwrites_source(self):
        with self.assertRaisesRegex(ValueError, "differ"):
            khocr_overlay("source.png", None, "source.png")

    def test_missing_dependency_is_actionable(self):
        with patch("khmereasytools.ocr._dependencies", side_effect=ImportError("Install khmereasytools[ocr]")):
            with self.assertRaisesRegex(ImportError, r"khmereasytools\[ocr\]"):
                khocr_layout("page.png")


if __name__ == "__main__":
    unittest.main()
