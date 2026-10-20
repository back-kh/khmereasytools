"""Model arithmetic, bounded data loading and segmentation isolation."""

import gzip
import hashlib
import io
import itertools
import json
import random
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from khmereasytools import khseg
from khmereasytools.compact_pos import CompactPOS, features, normalized, public_tag


def toy_model():
    return dict(format="ket-pos-crf-v1", scale=1000, labels=["NN", "VB"],
                state={"bias": [[0, 2], [1, -1]], "w=ក": [[1, 7]], "w=ខ": [[0, 5]]},
                transitions=[[1, 4], [-3, 2]],
                lexicon={"ក": [2, [[0, 1], [1, 1]]], "ខ": [3, [[0, 3]]]},
                metadata=dict(license="CC-BY-NC-SA-4.0", segmentation="frequency", training_sha256="a" * 64))


def packed(data):
    handle = io.BytesIO()
    with gzip.GzipFile(fileobj=handle, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    return handle.getvalue()


class CompactPOSTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "model.json.gz"

    def tearDown(self):
        self.directory.cleanup()

    def model(self, data=None):
        self.path.write_bytes(packed(toy_model() if data is None else data))
        return CompactPOS(self.path)

    def test_viterbi_matches_independent_exhaustive_paths(self):
        randomizer = random.Random(26020)
        for _ in range(35):
            data = toy_model()
            data["transitions"] = [[randomizer.randint(-10, 10) for _ in range(2)] for _ in range(2)]
            bias = [randomizer.randint(-5, 5) for _ in range(2)]
            emissions = {word: [randomizer.randint(-10, 10) for _ in range(2)] for word in ("ក", "ខ")}
            data["state"] = {"bias": [[i, n] for i, n in enumerate(bias)]}
            data["state"].update({"w=" + w: [[i, n] for i, n in enumerate(v)] for w, v in emissions.items()})
            model = self.model(data)
            words = [randomizer.choice(("ក", "ខ")) for _ in range(randomizer.randrange(1, 6))]

            def score(path):
                return (sum(bias[label] + emissions[word][label] for word, label in zip(words, path)) +
                        sum(data["transitions"][left][right] for left, right in zip(path, path[1:])))

            predicted = [model.labels.index(tag) for tag in model.predict(words)]
            self.assertEqual(score(predicted), max(score(path) for path in itertools.product(range(2), repeat=len(words))))

    def test_empty_input_ties_and_transition_direction(self):
        model = self.model()
        self.assertEqual(model.predict([]), [])
        data = toy_model()
        data["state"] = {"w=ក": [[0, 4]], "w=ខ": [[1, 4]]}
        data["transitions"] = [[0, 9], [-9, 0]]
        self.assertEqual(self.model(data).predict(["ក", "ខ"]), ["NN", "VB"])
        data = toy_model()
        data["state"] = {}
        data["transitions"] = [[0, 0], [0, 0]]
        self.assertEqual(self.model(data).predict(["ក", "ខ", "ក"]), ["NN"] * 3)

    def test_features_fold_digits_without_editing_source_or_coeng(self):
        self.assertEqual(normalized("១២៣"), normalized("123"))
        text = "ស្ត្រី"
        words = [text, "១២៣", "KET"]
        result = features(words, 0)
        self.assertIn("w=" + text, result)
        self.assertIn("BOS", result)
        self.assertIn("w+1=<NUMBER>", result)
        self.assertNotIn("EOS", result)
        self.assertEqual(words, [text, "១២៣", "KET"])
        self.assertEqual(public_tag("មិន", "RB"), "PART")
        self.assertEqual(public_tag("ណាស់", "RB"), "ADV")

    def test_model_segmentation_is_local_lossless_and_concurrent(self):
        data = toy_model()
        data["metadata"]["segmentation"] = "model"
        data["lexicon"]["កខ"] = [100, [[0, 100]]]
        model = self.model(data)
        text = "កខ\u200b ស្ត្រី\r\n១២៣។"
        before = khseg(text)
        # Include concurrent first use so a partial index/cost pair is caught.
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda unused: model.segment(text, ()), range(16)))
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual("".join(token.text for token in results[0]), text)
        for token in results[0]:
            self.assertEqual(text[token.start:token.end], token.text)
        self.assertEqual(khseg(text), before)

    def test_checksum_detects_changes(self):
        self.model()
        good = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(CompactPOS(self.path, expected_sha256=good).sha256, good)
        with self.assertRaises(ValueError):
            CompactPOS(self.path, expected_sha256="0" * 64)

    def test_invalid_schema_weights_indexes_and_provenance_are_rejected(self):
        cases = []
        for key, value in (("format", "pickle"), ("scale", True), ("labels", ["NN", "NN"]),
                           ("labels", ["UNKNOWN"]), ("transitions", [[0]]),
                           ("transitions", [[0, True], [0, 0]]),
                           ("state", {"bias": [[2, 1]]}), ("state", {"bias": [[-1, 1]]}),
                           ("state", {"bias": [[0, 1], [0, 2]]}),
                           ("state", {"bias": [[0, float("inf")]]}),
                           ("lexicon", {"word": [3, [[0, 2]]]}),
                           ("lexicon", {"word": [1, [[0, -1]]]}),
                           ("lexicon", {"two words": [1, [[0, 1]]]}), ("metadata", {})):
            data = toy_model()
            data[key] = value
            cases.append(data)
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.model(data)

    def test_non_json_and_truncated_gzip_fail_without_execution(self):
        for payload in (b"not gzip", b"\x80\x04pickle", packed(toy_model())[:-8],
                        b"\x1f\x8b\x08\x00" + b"\x00" * 6 + b"\xff" * 16):
            self.path.write_bytes(payload)
            with self.assertRaises(ValueError):
                CompactPOS(self.path)

    def test_compressed_and_decoded_size_limits(self):
        self.path.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            CompactPOS(self.path)
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb") as stream:
            stream.write(b" " * (24 * 1024 * 1024 + 1))
        self.path.write_bytes(buffer.getvalue())
        with self.assertRaises(ValueError):
            CompactPOS(self.path)


if __name__ == "__main__":
    unittest.main()
