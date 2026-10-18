import random
import unittest

from khmereasytools import khaudit, khdigits, khnormalize


class DigitTests(unittest.TestCase):
    def test_all_digits_round_trip(self):
        self.assertEqual(khdigits("០១២៣៤៥៦៧៨៩"), "0123456789")
        self.assertEqual(khdigits("0123456789", "khmer"), "០១២៣៤៥៦៧៨៩")

    def test_preserves_format_and_other_scripts(self):
        self.assertEqual(khdigits("០០៧ / ១២.៥% + ٣ ４"), "007 / 12.5% + ٣ ４")

    def test_validation(self):
        with self.assertRaises(TypeError):
            khdigits(123)
        with self.assertRaises(ValueError):
            khdigits("១", "latin")


class AuditTests(unittest.TestCase):
    def test_empty_and_nonletter_inputs(self):
        for text in ("", "១២៣ !"):
            report = khaudit(text)
            self.assertEqual(report.letter_count, 0)
            self.assertEqual(report.khmer_letter_ratio, 0.0)

    def test_ratio_counts_letters_only(self):
        report = khaudit("កា A ១😀")
        self.assertEqual(report.khmer_character_count, 3)
        self.assertEqual(report.khmer_letter_count, 1)
        self.assertEqual(report.letter_count, 2)
        self.assertEqual(report.khmer_letter_ratio, 0.5)

    def test_offsets_identify_actual_source(self):
        text = "😀\u200b\u17b4\ufffd\u202eកាា្"
        report = khaudit(text)
        codes = {issue.code for issue in report.issues}
        self.assertTrue({"zero_width_space", "discouraged_inherent_vowel",
                         "replacement_character", "bidi_control",
                         "repeated_khmer_mark", "dangling_coeng"} <= codes)
        for issue in report.issues:
            self.assertEqual(text[issue.start:issue.end], issue.text)
        self.assertEqual(report.issues[0].start, 1)  # code points, not UTF-16 units

    def test_valid_coeng_and_independent_vowel(self):
        for text in ("ខ្ញុំ", "ក្ត", "ក្\u17a5", "ប\u200c៊ីយែរ"):
            self.assertFalse([issue for issue in khaudit(text).issues
                              if issue.severity == "warning"], text)

    def test_orphan_after_boundary(self):
        codes = [issue.code for issue in khaudit("ក ា").issues]
        self.assertIn("orphan_khmer_mark", codes)

    def test_invalid_coeng(self):
        for text in ("្ក", "ក្", "ក្!", "ក្\u200d"):
            self.assertIn("dangling_coeng", [issue.code for issue in khaudit(text).issues])

    def test_shaping_controls_are_informational(self):
        report = khaudit("ប\u200c៊ី\u200d\u200b\u2060")
        self.assertTrue(report.issues)
        self.assertTrue(all(issue.severity == "info" for issue in report.issues))

    def test_unassigned_and_symbol_block(self):
        report = khaudit("\u17ff\u19e0")
        self.assertEqual(report.khmer_character_count, 1)
        self.assertEqual(report.issues[0].code, "unassigned_khmer")

    def test_controls_and_bom(self):
        codes = [issue.code for issue in khaudit("\ufeff\x00\t\n\r").issues]
        self.assertEqual(codes, ["bom", "control_character"])

    def test_type_error(self):
        with self.assertRaises(TypeError):
            khaudit(None)


class NormalizationTests(unittest.TestCase):
    def assert_trace(self, text, result):
        self.assertEqual(result.original, text)
        self.assertEqual(len(result.text), len(result.source_spans))
        last_end = 0
        for edit in result.edits:
            self.assertGreaterEqual(edit.start, last_end)
            self.assertGreater(edit.end, edit.start)
            self.assertEqual(edit.original, text[edit.start:edit.end])
            self.assertEqual(edit.replacement, result.text[edit.output_start:edit.output_end])
            self.assertTrue(edit.reason)
            last_end = edit.end
        forward = text
        for edit in reversed(result.edits):
            forward = forward[:edit.start] + edit.replacement + forward[edit.end:]
        self.assertEqual(forward, result.text)
        backward = result.text
        for edit in reversed(result.edits):
            backward = backward[:edit.output_start] + edit.original + backward[edit.output_end:]
        self.assertEqual(backward, text)
        previous_end = 0
        for start, end in result.source_spans:
            self.assertGreaterEqual(start, previous_end)
            self.assertLess(start, end)
            self.assertLessEqual(end, len(text))
            previous_end = end

    def test_default_is_conservative(self):
        text = "\ufeffខ្មែរ\u200b  ១២\r\nប\u200c៊ី\u17b4\ufffd\ufeff"
        result = khnormalize(text)
        self.assertEqual(result.text, text[1:].replace("\r\n", "\n"))
        self.assert_trace(text, result)

    def test_all_noop_options(self):
        text = "\ufeff  ក\r\n\u200b១\u17b4\u200d"
        result = khnormalize(text, remove_bom=False, normalize_newlines=False)
        self.assertEqual(result.text, text)
        self.assertEqual(result.edits, ())
        self.assertEqual(result.source_spans, tuple((i, i + 1) for i in range(len(text))))

    def test_opt_in_cleanup_and_mapping(self):
        text = "\ufeffក\u200b\t ១២\r\nខ្មែរ  "
        result = khnormalize(text, zero_width_space="space", digits="ascii",
                             collapse_spaces=True, strip=True)
        self.assertEqual(result.text, "ក 12\nខ្មែរ")
        self.assertEqual(result.source_spans[1], (2, 5))
        self.assert_trace(text, result)

    def test_deletions_between_spaces_collapse(self):
        text = "ក \u200b \u17b4 ខ"
        result = khnormalize(text, zero_width_space="remove", remove_inherent_vowels=True,
                             collapse_spaces=True)
        self.assertEqual(result.text, "ក ខ")
        self.assert_trace(text, result)

    def test_preserve_paragraph_boundaries(self):
        text = "ក  \n\nខ\u2028គ\rឃ"
        self.assertEqual(khnormalize(text, collapse_spaces=True).text, "ក \n\nខ\u2028គ\nឃ")

    def test_empty_and_all_removed(self):
        for text in ("", "\ufeff\ufeff", " \u200b \u17b4 "):
            result = khnormalize(text, zero_width_space="remove", strip=True,
                                 collapse_spaces=True, remove_inherent_vowels=True)
            self.assertEqual(result.text, "")
            self.assert_trace(text, result)

    def test_bom_exposed_by_cleanup(self):
        text = " \u200b\ufeff\ufeff ក"
        result = khnormalize(text, zero_width_space="remove", strip=True)
        self.assertEqual(result.text, "ក")
        self.assert_trace(text, result)

    def test_no_implicit_unicode_reordering(self):
        text = "e\u0301ក\u17b7\u17c6"
        self.assertEqual(khnormalize(text).text, text)

    def test_validation(self):
        with self.assertRaises(TypeError):
            khnormalize(b"text")
        for option in ({"digits": "invalid"}, {"zero_width_space": "invalid"}):
            with self.assertRaises(ValueError):
                khnormalize("text", **option)

    def test_randomized_trace_and_idempotence(self):
        rng = random.Random(20261018)
        alphabet = "កខា្ិ១២3A😀 \t\n\r\ufeff\u200b\u200c\u200d\u17b4\u17b5\u00a0\u2028"
        for _ in range(1000):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(60)))
            options = dict(zero_width_space=rng.choice(("preserve", "space", "remove")),
                           digits=rng.choice(("preserve", "ascii", "khmer")),
                           collapse_spaces=rng.choice((True, False)),
                           strip=rng.choice((True, False)),
                           remove_bom=rng.choice((True, False)),
                           normalize_newlines=rng.choice((True, False)),
                           remove_inherent_vowels=rng.choice((True, False)))
            result = khnormalize(text, **options)
            with self.subTest(text=repr(text), options=options):
                self.assert_trace(text, result)
                second = khnormalize(result.text, **options)
                self.assertEqual(result.text, second.text)
                self.assertEqual(second.edits, ())


if __name__ == "__main__":
    unittest.main()
