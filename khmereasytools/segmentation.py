"""Lossless dictionary segmentation with a global maximum-coverage decoder."""

import unicodedata
from functools import lru_cache
from typing import NamedTuple

from .lexicon import _words, _frequency_costs
from .text_quality import _is_base, _is_mark, _require_text


class TokenSpan(NamedTuple):
    text: str
    start: int
    end: int
    kind: str


def _kind(char):
    if char.isspace():
        return "whitespace"
    if char == "\u200b":
        return "boundary"
    if char.isdecimal():
        return "number"
    if unicodedata.category(char).startswith("P"):
        return "punctuation"
    if _is_base(char) or _is_mark(char) or char in "\u200c\u200d":
        return "unknown_khmer"
    if ord(char) < 128 and char.isalnum():
        return "latin"
    return "other"


def _validated_words(words):
    if isinstance(words, (str, bytes)):
        raise TypeError("words must be an iterable of nonempty strings, not a string")
    result = set()
    for word in words:
        if not isinstance(word, str):
            raise TypeError("every dictionary word must be a str")
        if not word or not word.strip():
            raise ValueError("dictionary words must not be empty or whitespace-only")
        result.add(word)
    return result


def _index(words):
    # Store each word once, plus candidate lengths by its first two code
    # points. This avoids a Python dict object for every character-trie node.
    prefixes = {}
    for word in words:
        if len(word) > 1:
            prefixes.setdefault(word[:2], set()).add(len(word))
    return words, {prefix: tuple(sorted(lengths, reverse=True))
                   for prefix, lengths in prefixes.items()}


@lru_cache(maxsize=2)
def _default_index(dictionary):
    return _index(_words(dictionary))


def khseg_spans(text, custom_words=None, *, dictionary="expanded", strategy="frequency"):
    """Return tokens whose concatenation exactly reconstructs the input.

    'frequency' minimizes unknown Khmer code points, then summed smoothed
    unigram costs from a bundled frequency table. 'coverage' instead minimizes
    unknown code points then token count. Equal costs prefer longer first matches.
    'longest' uses greedy longest matching. Counts are ranking preferences,
    not calibrated confidence. No runtime model or download is required.
    dictionary accepts 'expanded', 'legacy', or an iterable for a local lexicon.
    Custom words add exact candidates without changing the shared dictionary.
    """
    return _segment_spans(text, custom_words, dictionary=dictionary, strategy=strategy)


def _segment_spans(text, custom_words=None, *, dictionary="expanded", strategy="frequency",
                   _word_costs=None, _prepared_index=None):
    """Shared decoder; model-specific indexes/costs stay local to the tagger."""
    _require_text(text)
    if strategy not in ("frequency", "coverage", "longest"):
        raise ValueError("strategy must be 'frequency', 'coverage' or 'longest' for lossless spans")
    if not text:
        if isinstance(dictionary, str):
            if dictionary not in ("expanded", "legacy"):
                raise ValueError("dictionary must be 'expanded' or 'legacy'")
        else:
            _validated_words(dictionary)
        if custom_words is not None:
            _validated_words(custom_words)
        return []
    indexes = [_prepared_index if _prepared_index is not None else
               _default_index(dictionary) if isinstance(dictionary, str) else _index(_validated_words(dictionary))]
    custom = _validated_words(custom_words) if custom_words is not None else set()
    if custom:
        indexes.append(_index(custom))
    weighted = strategy == "frequency" and (_word_costs is not None or
                isinstance(dictionary, str) and dictionary == "expanded")
    weights, missing_cost = _word_costs if _word_costs is not None else _frequency_costs() if weighted else ({}, 1)

    def word_cost(start, end):
        word = text[start:end]
        if weighted and word in custom:
            return 1
        return weights.get(word, missing_cost)
    length = len(text)
    kinds = [_kind(char) for char in text]
    boundaries, previous = [], ""
    for char in text:
        boundaries.append(not (_is_mark(char) or char in "\u200c\u200d" or previous == "\u17d2"))
        if char not in "\u200c\u200d":
            previous = char
    boundaries.append(previous != "\u17d2")

    def matches(start):
        if not boundaries[start]:
            return ()
        ends = set()
        for words, prefixes in indexes:
            if boundaries[start + 1] and text[start:start + 1] in words:
                ends.add(start + 1)
            for size in prefixes.get(text[start:start + 2], ()):
                end = start + size
                if end <= length and boundaries[end] and text[start:end] in words:
                    ends.add(end)
        return sorted(ends, reverse=True)

    # An unknown Khmer fallback consumes one structurally safe unit. Other
    # runs can be grouped, while respecting starts of caller-supplied words.
    fallback = [0] * length
    for start in range(length - 1, -1, -1):
        end = start + 1
        if kinds[start] == "unknown_khmer":
            if end < length and kinds[end] == "unknown_khmer" and not boundaries[end]:
                end = fallback[end]
        elif kinds[start] not in ("punctuation", "other", "boundary"):
            if end < length and kinds[start] == kinds[end] and not matches(end):
                end = fallback[end]
        fallback[start] = end

    if strategy == "longest":
        steps = []
        position = 0
        while position < length:
            ends = matches(position)
            end = ends[0] if ends else fallback[position]
            steps.append((position, end, "word" if ends else kinds[position]))
            position = end
    else:
        # Dynamic programming over character positions. No evaluation-set
        # vocabulary or counts enter the scoring rule.
        costs = [[(0, 0)] * (length + 1) for _ in range(2)]
        choices = [[None] * length for _ in range(2)]
        for start in range(length - 1, -1, -1):
            word_best, word_choice = None, None
            for end in matches(start):
                cost = (costs[0][end][0], costs[0][end][1] +
                        (word_cost(start, end) if strategy == "frequency" else 1))
                if word_best is None or cost < word_best:
                    word_best, word_choice = cost, (end, "word")
            end, kind = fallback[start], kinds[start]
            is_unknown = kind == "unknown_khmer"
            unknown = end - start if is_unknown else 0
            # Two states account for adjacent unknown units merging into one
            # output token; the secondary score counts actual output tokens.
            for preceding_unknown in (0, 1):
                suffix = costs[int(is_unknown)][end]
                candidate = (suffix[0] + unknown,
                             suffix[1] + (missing_cost if weighted and is_unknown else 1) *
                             int(not (is_unknown and preceding_unknown)))
                if word_best is None or candidate < word_best:
                    costs[preceding_unknown][start] = candidate
                    choices[preceding_unknown][start] = (end, kind)
                else:
                    costs[preceding_unknown][start] = word_best
                    choices[preceding_unknown][start] = word_choice
        steps, position, state = [], 0, 0
        while position < length:
            end, kind = choices[state][position]
            steps.append((position, end, kind))
            position, state = end, int(kind == "unknown_khmer")

    tokens = []
    for start, end, kind in steps:
        if kind == "unknown_khmer" and tokens and tokens[-1].kind == kind:
            previous = tokens.pop()
            tokens.append(TokenSpan(text[previous.start:end], previous.start, end, kind))
        else:
            tokens.append(TokenSpan(text[start:end], start, end, kind))
    return tokens
