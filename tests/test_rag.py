import json
import os
import subprocess
import sys
import tempfile
import unittest

from khmereasytools import KhmerRAG, khrag


class KhmerRAGTests(unittest.TestCase):
    def test_khmer_retrieval_retains_source_and_exact_offsets(self):
        documents = {"school": "សិស្សអានសៀវភៅនៅសាលារៀន។", "food": "ខ្ញុំញ៉ាំបាយ។"}
        result = khrag("សៀវភៅ", documents)
        self.assertIsNone(result.answer)
        self.assertFalse(result.generated)
        self.assertEqual(result.sources[0].document_id, "school")
        for source in result.sources:
            self.assertEqual(documents[source.document_id][source.start:source.end], source.text)
        self.assertIn("[1] " + documents["school"], result.context)

    def test_generator_receives_only_matched_evidence_and_citation_mapping(self):
        calls = []
        def generate(prompt):
            calls.append(prompt)
            return "សិស្សអានសៀវភៅ។ [1]"
        result = KhmerRAG({"school": "សិស្សអានសៀវភៅ។", "food": "ខ្ញុំញ៉ាំបាយ។"}, generator=generate).ask("សៀវភៅ")
        self.assertTrue(result.generated)
        self.assertEqual(result.answer, "សិស្សអានសៀវភៅ។ [1]")
        payload = json.loads(calls[0].split("\n\n", 1)[1])
        self.assertEqual(payload["question"], "សៀវភៅ")
        self.assertEqual(payload["sources"], [{"citation": 1, "text": result.sources[0].text}])
        self.assertNotIn("ខ្ញុំញ៉ាំបាយ", calls[0])

    def test_no_match_or_empty_collection_never_generates(self):
        def fail(prompt):
            self.fail("No evidence must not invoke the generator")
        for documents in ([], ["សៀវភៅ"]):
            result = KhmerRAG(documents, generator=fail).ask("astronomy")
            self.assertEqual(result.sources, ())
            self.assertEqual(result.context, "")
            self.assertIsNone(result.answer)
            self.assertFalse(result.generated)

    def test_chunking_covers_sources_without_breaking_coeng_or_combining_sequences(self):
        from khmereasytools.rag import _boundary, _chunks
        text = ("សិស្សអានសៀវភៅនៅសាលារៀន។\n" * 30) + "a" + "\u0301" * 100
        covered = set()
        chunks = list(_chunks(text, 64, 12))
        self.assertGreater(len(chunks), 2)
        for start, end in chunks:
            self.assertTrue(_boundary(text, start))
            self.assertTrue(_boundary(text, end))
            self.assertGreater(end, start)
            covered.update(range(start, end))
        self.assertEqual(covered, set(range(len(text))))
        rag = KhmerRAG({7: text}, chunk_size=64, overlap=12)
        for source in rag.retrieve("សៀវភៅ", limit=5):
            self.assertEqual(source.text, text[source.start:source.end])
            self.assertEqual(source.document_id, 7)

    def test_reuse_and_latin_digit_matching(self):
        rag = KhmerRAG(["Invoice លេខ១២៣"], chunk_size=64, overlap=0)
        self.assertTrue(khrag("invoice 123", rag).sources)
        with self.assertRaises(ValueError):
            khrag("invoice", rag, generator=lambda text: text)

    def test_invalid_inputs_and_generator_outputs(self):
        for docs in ("text", {True: "text"}, [None]):
            with self.subTest(docs=docs), self.assertRaises(TypeError):
                KhmerRAG(docs)
        for options in ({"chunk_size": 0}, {"chunk_size": True}, {"overlap": -1}, {"overlap": 800}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                KhmerRAG([], **options)
        with self.assertRaises(TypeError):
            KhmerRAG([], generator="model-name")
        for invalid in (None, "", []):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                KhmerRAG(["cat"], generator=lambda prompt: invalid).ask("cat")
        with self.assertRaises(ValueError):
            KhmerRAG([]).ask("cat", limit=False)

    def test_cli_retrieval_needs_no_model_and_emits_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = os.path.join(folder, "សៀវភៅ.txt")
            with open(filename, "w", encoding="utf-8") as handle:
                handle.write("សិស្សអានសៀវភៅ។")
            result = subprocess.run([sys.executable, "-m", "khmereasytools", "rag", "សៀវភៅ", filename],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout.decode())
        self.assertFalse(data["generated"])
        self.assertIsNone(data["answer"])
        self.assertEqual(data["sources"][0]["document_id"], filename)


if __name__ == "__main__":
    unittest.main()
