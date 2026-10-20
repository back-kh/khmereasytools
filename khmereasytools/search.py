"""Small, in-memory Khmer keyword retrieval with no external dependencies."""

import math
from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import NamedTuple, Tuple, Union

from .segmentation import khseg_spans, _validated_words
from .text_quality import _require_text, khdigits


class SearchMatch(NamedTuple):
    text: str
    start: int
    end: int


class SearchHit(NamedTuple):
    document_id: Union[str, int]
    score: float
    text: str
    snippet: str
    matches: Tuple[SearchMatch, ...]


def _term(text):
    return khdigits(text).casefold()


def _is_khmer_term(text):
    return bool(text) and all("\u1780" <= char <= "\u17ff" for char in text)


def _terms(text, custom_words):
    for token in khseg_spans(text, custom_words=custom_words):
        searchable = token.kind in ("word", "unknown_khmer", "latin", "number") or (
            token.kind == "other" and token.text.isalpha())
        if searchable and any(char.isalpha() or char.isdecimal() for char in token.text):
            yield _term(token.text), token


def _snippet(text, matches, size=160):
    start = max(0, matches[0].start - size // 3)
    end = min(len(text), max(start + size, matches[0].end))
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


class KhmerSearchIndex:
    """Reusable BM25 index for a small local collection of strings.

    Mapping keys are string/integer IDs; a sequence gets zero-based IDs.
    Scores rank this collection, not probabilities. Khmer substring recall
    within tokens handles dictionary compounds, with a lower weight than
    exact terms. No stemming, semantic model, OCR correction, or translation
    is applied. The index is a snapshot; rebuilding applies document changes.
    """

    def __init__(self, documents, *, custom_words=None):
        if isinstance(documents, (str, bytes)):
            raise TypeError("documents must be strings in an iterable or an ID-to-text mapping")
        self._custom_words = None if custom_words is None else tuple(sorted(_validated_words(custom_words)))
        items = documents.items() if isinstance(documents, Mapping) else enumerate(documents)
        self._documents = {}
        self._postings = defaultdict(dict)
        self._positions = {}
        self._lengths = {}
        for document_id, text in items:
            if isinstance(document_id, bool) or not isinstance(document_id, (str, int)):
                raise TypeError("document IDs must be strings or integers")
            _require_text(text)
            self._documents[document_id] = text
            positions = defaultdict(list)
            for term, token in _terms(text, self._custom_words):
                positions[term].append(token)
            self._positions[document_id] = positions
            self._lengths[document_id] = sum(len(tokens) for tokens in positions.values())
            for term, tokens in positions.items():
                self._postings[term][document_id] = len(tokens)
        self._vocabulary = tuple(sorted(self._postings))
        self._average_length = sum(self._lengths.values()) / max(1, len(self._documents))

    def __len__(self):
        return len(self._documents)

    def get(self, document_id):
        """Retrieve the unchanged source text by its ID; missing IDs raise KeyError."""
        return self._documents[document_id]

    def search(self, query, *, limit=5, match="any"):
        """Return ranked hits, source offsets, and snippets for a Khmer/Latin query.

        Latin case and Khmer/ASCII digits are folded only for matching. Source
        strings are unchanged. match='all' requires each distinct query term.
        Matching inside a Khmer compound scans the vocabulary, so this index
        targets everyday collections rather than a large search service.
        """
        _require_text(query)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if match not in ("any", "all"):
            raise ValueError("match must be 'any' or 'all'")
        query_terms = sorted({term for term, _ in _terms(query, self._custom_words)})
        if not query_terms or not self._documents:
            return []
        scores, counts = defaultdict(float), Counter()
        matched_terms = defaultdict(set)
        total = len(self._documents)
        for term in query_terms:
            # Fold digits/Latin case without changing source text or offsets.
            # Partial Khmer matches recover a query such as ខ្មែរ from an
            # indexed dictionary compound such as ភាសាខ្មែរ.
            variants = [term] if term in self._postings else []
            if _is_khmer_term(term):
                variants.extend(word for word in self._vocabulary
                                if word != term and _is_khmer_term(word) and term in word)
            frequencies = defaultdict(float)
            for word in variants:
                weight = 1.0 if word == term else 0.5 * len(term) / len(word)
                for document_id, frequency in self._postings[word].items():
                    frequencies[document_id] += weight * frequency
                    matched_terms[document_id].add(word)
            if not frequencies:
                continue
            inverse_frequency = math.log(1 + (total - len(frequencies) + 0.5) / (len(frequencies) + 0.5))
            for document_id, frequency in frequencies.items():
                length = self._lengths[document_id] / (self._average_length or 1)
                scores[document_id] += inverse_frequency * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length))
                counts[document_id] += 1
        order = {document_id: position for position, document_id in enumerate(self._documents)}
        candidates = [document_id for document_id in scores
                      if match == "any" or counts[document_id] == len(query_terms)]
        candidates.sort(key=lambda document_id: (-scores[document_id], order[document_id]))
        hits = []
        for document_id in candidates[:limit]:
            text = self._documents[document_id]
            tokens = [token for term in matched_terms[document_id]
                      for token in self._positions[document_id][term]]
            tokens.sort(key=lambda token: (token.start, token.end))
            # Highlight full source tokens, including the enclosing compound.
            matches = tuple(SearchMatch(token.text, token.start, token.end) for token in tokens)
            hits.append(SearchHit(document_id, scores[document_id], text, _snippet(text, matches), matches))
        return hits


def khindex(documents, *, custom_words=None):
    """Build a reusable local index from strings or an ID-to-text mapping."""
    return KhmerSearchIndex(documents, custom_words=custom_words)


def khsearch(query, documents, *, limit=5, match="any"):
    """Search strings directly, or reuse an index returned by khindex."""
    index = documents if isinstance(documents, KhmerSearchIndex) else khindex(documents)
    return index.search(query, limit=limit, match=match)
