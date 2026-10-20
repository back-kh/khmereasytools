import math
import unittest

from khmereasytools import KhmerSearchIndex, khindex, khsearch


class SearchTests(unittest.TestCase):
    def test_khmer_retrieval_and_original_offsets(self):
        documents = {"school": "សិស្សអានសៀវភៅនៅសាលារៀន។", "food": "ខ្ញុំញ៉ាំបាយ។"}
        hits = khsearch("សៀវភៅ", documents)
        self.assertEqual([hit.document_id for hit in hits], ["school"])
        self.assertEqual(hits[0].text, documents["school"])
        self.assertIn("សៀវភៅ", hits[0].snippet)
        self.assertGreater(hits[0].score, 0)
        for found in hits[0].matches:
            self.assertEqual(found.text, hits[0].text[found.start:found.end])

    def test_compound_recall_and_exact_preference(self):
        hits = khsearch("ខ្មែរ", ["ខ្មែរ", "ភាសាខ្មែរ", "សៀវភៅ"])
        self.assertEqual([hit.document_id for hit in hits], [0, 1])
        self.assertEqual(hits[1].matches[0].text, "ភាសាខ្មែរ")

    def test_reusable_index_snapshot_and_retrieve(self):
        documents = {"one": "សៀវភៅ", 2: "ភាសាខ្មែរ"}
        index = khindex(documents)
        documents["one"] = "changed"
        self.assertIsInstance(index, KhmerSearchIndex)
        self.assertEqual(len(index), 2)
        self.assertEqual(index.get("one"), "សៀវភៅ")
        self.assertEqual(khsearch("សៀវភៅ", index), index.search("សៀវភៅ"))
        with self.assertRaises(KeyError):
            index.get("missing")

    def test_case_digits_and_mixed_query(self):
        index = khindex(["Python ២០២៦ សៀវភៅ", "python 2025", "សៀវភៅ"])
        hits = index.search("PYTHON 2026", match="all")
        self.assertEqual([hit.document_id for hit in hits], [0])
        self.assertEqual([found.text for found in hits[0].matches], ["Python", "២០២៦"])
        self.assertEqual(index.search("2025")[0].document_id, 1)
        self.assertEqual(index.search("py"), [])  # Latin words are exact terms.

    def test_all_requires_every_distinct_term(self):
        index = khindex(["cat dog", "cat", "dog", "bird"])
        self.assertEqual([hit.document_id for hit in index.search("cat dog", match="all")], [0])
        self.assertEqual(index.search("cat missing", match="all"), [])
        self.assertEqual(index.search("cat cat"), index.search("cat"))
        self.assertEqual(len(index.search("cat dog", limit=2)), 2)

    def test_bm25_against_hand_calculation(self):
        hits = khsearch("cat", ["cat cat", "dog"])
        # N=2, df=1, tf=2, dl=2, average dl=1.5, k1=1.2, b=.75.
        expected = math.log(2) * (2 * 2.2) / (2 + 1.2 * (0.25 + 0.75 * 2 / 1.5))
        self.assertAlmostEqual(hits[0].score, expected)

    def test_stable_ties_and_empty_documents(self):
        index = khindex({"z": "cat", "a": "cat", "empty": ""})
        self.assertEqual([hit.document_id for hit in index.search("cat")], ["z", "a"])
        self.assertTrue(all(math.isfinite(hit.score) for hit in index.search("cat")))
        for query in ("", "  ", "?!", "ា", "missing"):
            self.assertEqual(index.search(query), [])
        self.assertEqual(khsearch("cat", []), [])

    def test_custom_vocabulary_generator_used_for_documents_and_query(self):
        index = khindex(["ឋឍ"], custom_words=(word for word in ["ឋឍ"]))
        self.assertEqual(index.search("ឋឍ")[0].text, "ឋឍ")

    def test_long_source_snippet_and_offsets(self):
        source = "intro " * 100 + "សៀវភៅ" + " ending" * 100
        hit = khsearch("សៀវភៅ", [source])[0]
        self.assertTrue(hit.snippet.startswith("…"))
        self.assertIn("សៀវភៅ", hit.snippet)
        self.assertLess(len(hit.snippet), len(source))
        self.assertEqual(hit.matches[0].start, 600)

    def test_validation(self):
        for documents in ("not a collection", b"bytes", [None], {None: "text"}, {True: "text"}):
            with self.subTest(documents=documents), self.assertRaises(TypeError):
                khindex(documents)
        index = khindex(["cat"])
        with self.assertRaises(TypeError):
            index.search(None)
        for limit in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                index.search("cat", limit=limit)
        with self.assertRaises(ValueError):
            index.search("cat", match="other")


if __name__ == "__main__":
    unittest.main()
