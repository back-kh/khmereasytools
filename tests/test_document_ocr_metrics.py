"""Protect evaluation validity across heterogeneous full-page backends."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from document_ocr_metrics import scored_record, summarize, visible_text
from fetch_document_ocr import manuscript_group
from audit_document_ocr import score as independent_score, self_check
from evaluation_metrics import text_score


class DocumentMetricsTests(unittest.TestCase):
    def test_independent_distance_audit_and_unicode_projections(self):
        self.assertEqual(self_check(), 1039)
        cases = [("", ""), ("កខ", ""), ("ក" * 80, "ខ" * 120),
                 ("a\u0301 ក\u200b ខ\n12", "á\tកខ 13"),
                 ("ក ខ abc", "ក ខ abc abc"), ("one two", "two one")]
        for reference, prediction in cases:
            self.assertEqual(independent_score(reference, prediction),
                             text_score(reference, prediction))

    def page(self, **extra):
        return dict(id="one", collection="churro-sleuk", group="book", source_split="test",
                    reference="សួស្តី abc", **extra)

    def test_html_metadata_is_not_recognized_text(self):
        raw = '<style>p {color:red}</style><div data-bbox="1 2 3 4"><p>សួស្តី &amp; abc</p></div>'
        self.assertEqual(visible_text(raw), "សួស្តី & abc")

    def test_markdown_table_serialization_preserves_cell_contents(self):
        raw = "```markdown\n| **ឈ្មោះ** | [abc](https://example.com) |\n| --- | --- |\n| តម្លៃ | 12.50 |\n```"
        text = visible_text(raw)
        self.assertIn("ឈ្មោះ", text)
        self.assertIn("12.50", text)
        self.assertNotIn("https", text)
        self.assertNotIn("---", text)
        self.assertNotIn("|", text)

    def test_failure_and_empty_success_both_keep_reference_denominators(self):
        rows = [scored_record(self.page(), "a", "", 1, error="timeout"),
                scored_record(self.page(), "a", "", 1)]
        score = summarize(rows)["churro-sleuk"]["a"]
        self.assertEqual(score["compact_codepoint_cer"], 1)
        self.assertEqual(score["samples"], 2)
        self.assertEqual(score["failures"], 1)
        self.assertEqual(score["empty"], 2)

    def test_error_with_partial_output_is_scored_without_discarding_text(self):
        row = scored_record(self.page(), "a", "សួស្តី", 1, error="one block failed")
        score = summarize([row])["churro-sleuk"]["a"]
        self.assertGreater(score["compact_codepoint_cer"], 0)
        self.assertLess(score["compact_codepoint_cer"], 1)
        self.assertEqual(score["failures"], 1)

    def test_source_split_results_are_not_pooled_with_printed_pages(self):
        historical = scored_record(self.page(), "a", "សួស្តី abc", 1)
        printed = dict(self.page(), collection="wikisource-printed", source_split="proofread")
        result = summarize([historical, scored_record(printed, "a", "", 1)])
        self.assertEqual(result["churro-sleuk-test"]["a"]["compact_codepoint_cer"], 0)
        self.assertEqual(result["wikisource-printed"]["a"]["compact_codepoint_cer"], 1)

    def test_manuscript_groups_combine_related_leaves(self):
        self.assertEqual(manuscript_group("sleuk/411_nl_a140_015_01"),
                         manuscript_group("sleuk/362_nl_a140_029_02"))
        self.assertEqual(manuscript_group("sleuk/337_pp_ttp_02_013"), "sleuk/pp_ttp_02")
        self.assertNotEqual(manuscript_group("sleuk/337_pp_ttp_02_013"),
                            manuscript_group("sleuk/120_pp_ttp_01_004"))


if __name__ == "__main__":
    unittest.main()
