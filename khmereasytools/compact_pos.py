"""Small supervised POS inference; MIT code, separately licensed research data.

Only gzip/JSON weights are read. CRFsuite is used by the offline training
script, never imported here. Integer Viterbi scores are not probabilities.
"""

import gzip
import hashlib
import io
import json
import math
import unicodedata
import zlib
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from .lexicon import _words
from .segmentation import _index, _segment_spans


NATIVE_TO_PUBLIC = {
    "AB": "NOUN", "AUX": "AUX", "CC": "CCONJ", "CD": "NUM", "DBL": "PART",
    "DT": "DET", "ETC": "ADV", "IN": "ADP", "JJ": "ADJ", "KAN": "PUNCT",
    "M": "NOUN", "NN": "NOUN", "PA": "PART", "PN": "PROPN", "PRO": "PRON",
    "QT": "PART", "RB": "ADV", "RPN": "PRON", "SYM": "SYM", "UH": "INTJ",
    "VB": "VERB", "VB_JJ": "ADJ", "VCOM": "VERB",
}
_NEGATIVE = frozenset(("មិន", "ពុំ", "កុំ", "មិនមែន", "មិនទាន់", "ទេ"))
_MAX_COMPRESSED = 2 * 1024 * 1024
_MAX_DECODED = 24 * 1024 * 1024
_MODEL_FILE = Path(__file__).parent / "data/research/ket_pos_v2.json.gz"


def _json_integer(value):
    if len(value) > 12:
        raise ValueError("POS model integer is too large")
    return int(value)


def _json_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("POS model numbers must be finite")
    return result


def public_tag(word, native):
    if native == "RB" and word in _NEGATIVE:
        return "PART"
    return NATIVE_TO_PUBLIC[native]


def normalized(word):
    word = unicodedata.normalize("NFC", word).lower()
    if word.isdecimal():
        return "<NUMBER>"
    return "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in word)


def _shape(word):
    if word.isdecimal():
        return "number"
    if all(unicodedata.category(c).startswith("P") for c in word):
        return "punctuation"
    if all(unicodedata.category(c).startswith("S") for c in word):
        return "symbol"
    if all("\u1780" <= c <= "\u17ff" or c in "\u200c\u200d" for c in word):
        return "khmer"
    if all(ord(c) < 128 for c in word):
        return "latin"
    return "mixed"


def features(words, position):
    """Shared deterministic training/inference feature strings, not token edits."""
    word = normalized(words[position])
    result = ["bias", "w=" + word, "shape=" + _shape(words[position]),
              "len=" + str(min(len(word), 16))]
    for size in (1, 2, 3):
        result.append("p{}={}".format(size, word[:size]))
        result.append("s{}={}".format(size, word[-size:]))
    for prefix in ("ការ", "ភាព", "សេចក្តី", "សេចក្ដី"):
        if word.startswith(prefix):
            result.append("nominal=" + prefix)
    for offset in (-2, -1, 1, 2):
        index = position + offset
        if 0 <= index < len(words):
            result.append("w{:+d}={}".format(offset, normalized(words[index])))
            if abs(offset) == 1:
                result.append("shape{:+d}={}".format(offset, _shape(words[index])))
        else:
            result.append("edge{:+d}".format(offset))
    if position == 0:
        result.append("BOS")
    if position + 1 == len(words):
        result.append("EOS")
    return result


def _integer(value, bound=1000000):
    return isinstance(value, int) and not isinstance(value, bool) and abs(value) <= bound


class CompactPOS:
    """Read-only CRF weights and training-local vocabulary for repeated calls."""

    def __init__(self, path, *, expected_sha256=None):
        path = Path(path)
        with path.open("rb") as handle:
            packed = handle.read(_MAX_COMPRESSED + 1)
        if len(packed) > _MAX_COMPRESSED:
            raise ValueError("POS model exceeds the 2 MiB compressed limit")
        self.sha256 = hashlib.sha256(packed).hexdigest()
        if expected_sha256 is not None and self.sha256 != expected_sha256:
            raise ValueError("POS model checksum mismatch")
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
                raw = stream.read(_MAX_DECODED + 1)
            if len(raw) > _MAX_DECODED:
                raise ValueError("POS model exceeds the decoded size limit")
            data = json.loads(raw.decode("utf-8"), parse_int=_json_integer,
                              parse_float=_json_float, parse_constant=_json_float)
        except (OSError, EOFError, UnicodeError, json.JSONDecodeError, RecursionError, zlib.error) as exc:
            raise ValueError("POS model is not valid gzip UTF-8 JSON") from exc
        self._load(data)

    def _load(self, data):
        if not isinstance(data, dict) or data.get("format") != "ket-pos-crf-v1" or data.get("scale") != 1000:
            raise ValueError("Unsupported POS model format or scale")
        labels = data.get("labels")
        if (not isinstance(labels, list) or not labels or len(labels) > 23 or
                any(not isinstance(label, str) or label not in NATIVE_TO_PUBLIC for label in labels) or
                len(set(labels)) != len(labels)):
            raise ValueError("Invalid POS label inventory")
        count = len(labels)
        transitions = data.get("transitions")
        if (not isinstance(transitions, list) or len(transitions) != count or
                any(not isinstance(row, list) or len(row) != count or
                    any(not _integer(value) for value in row) for row in transitions)):
            raise ValueError("Invalid POS transition matrix")
        state, words = data.get("state"), data.get("lexicon")
        if not isinstance(state, dict) or len(state) > 150000 or not isinstance(words, dict) or len(words) > 50000:
            raise ValueError("Invalid POS feature/vocabulary table")

        def vector(values):
            if not isinstance(values, list) or len(values) > count:
                raise ValueError("Invalid sparse POS vector")
            indexes, result = set(), []
            for pair in values:
                if (not isinstance(pair, list) or len(pair) != 2 or
                        not _integer(pair[0], count - 1) or pair[0] < 0 or pair[0] in indexes or
                        not _integer(pair[1])):
                    raise ValueError("Invalid POS index/weight")
                indexes.add(pair[0])
                result.append(tuple(pair))
            return tuple(result)

        weights, vocabulary, lexical = {}, {}, {}
        for feature, values in state.items():
            if not isinstance(feature, str) or not feature or len(feature) > 3000:
                raise ValueError("Invalid POS feature name")
            weights[feature] = vector(values)
        for word, entry in words.items():
            if (not isinstance(word, str) or not word or len(word) > 1000 or
                    any(c.isspace() or c == "\u200b" for c in word) or
                    not isinstance(entry, list) or len(entry) != 2 or
                    not _integer(entry[0]) or entry[0] <= 0):
                raise ValueError("Invalid POS vocabulary entry")
            distribution = vector(entry[1])
            if not distribution or any(c <= 0 for _, c in distribution) or sum(c for _, c in distribution) != entry[0]:
                raise ValueError("Invalid POS lexical counts")
            vocabulary[word], lexical[word] = entry[0], distribution
        metadata = data.get("metadata")
        if (not isinstance(metadata, dict) or metadata.get("license") != "CC-BY-NC-SA-4.0" or
                metadata.get("segmentation") not in ("frequency", "model") or
                not isinstance(metadata.get("training_sha256"), str) or len(metadata["training_sha256"]) != 64):
            raise ValueError("Missing POS provenance, license or segmentation profile")
        self.labels = tuple(labels)
        self.state = MappingProxyType(weights)
        self.transitions = tuple(tuple(row) for row in transitions)
        self._incoming = tuple(tuple(row[i] for row in transitions) for i in range(count))
        self.word_counts = MappingProxyType(vocabulary)
        self.lexical = MappingProxyType(lexical)
        self.metadata = MappingProxyType(dict(metadata))
        self._segmentation = None

    def predict(self, words):
        """Exact Viterbi for the stored integer model; no calibrated confidence."""
        if not words:
            return []
        count, previous, paths = len(self.labels), None, []
        for position in range(len(words)):
            emission = [0] * count
            for feature in features(words, position):
                for tag, weight in self.state.get(feature, ()):
                    emission[tag] += weight
            if previous is None:
                previous = emission
                continue
            following, back = [], []
            for tag in range(count):
                incoming = self._incoming[tag]
                best, best_tag = previous[0] + incoming[0], 0
                for source in range(1, count):
                    value = previous[source] + incoming[source]
                    if value > best:
                        best, best_tag = value, source
                following.append(best + emission[tag])
                back.append(best_tag)
            previous = following
            paths.append(back)
        last = max(range(count), key=previous.__getitem__)
        result = [last]
        for back in reversed(paths):
            last = back[last]
            result.append(last)
        return [self.labels[index] for index in reversed(result)]

    def segment(self, text, custom_words, *, profile=None):
        profile = self.metadata["segmentation"] if profile is None else profile
        if profile not in ("frequency", "model"):
            raise ValueError("Invalid model segmentation profile")
        if profile == "frequency":
            return _segment_spans(text, custom_words=custom_words)
        if self._segmentation is None:
            # Cached, model-local candidates; never edit the core dictionary.
            index = _index(frozenset(_words("expanded")) | frozenset(self.word_counts))
            total = sum(self.word_counts.values()) + 0.1 * (len(self.word_counts) + 1)
            costs = {word: max(1, round(-math.log((count + 0.1) / total) * 1000000))
                     for word, count in self.word_counts.items()}
            # Publish the pair together, including on a shared first call.
            self._segmentation = (index, (costs, round(-math.log(0.1 / total) * 1000000)))
        index, costs = self._segmentation
        return _segment_spans(text, custom_words=custom_words, _word_costs=costs,
                              _prepared_index=index)


@lru_cache(maxsize=1)
def default_model():
    manifest = json.loads(_MODEL_FILE.with_name("manifest.json").read_text(encoding="utf-8"))
    expected = manifest.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("Invalid bundled POS model manifest")
    return CompactPOS(_MODEL_FILE, expected_sha256=expected)
