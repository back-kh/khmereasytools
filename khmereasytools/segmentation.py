"""Lossless dictionary segmentation for annotation and custom vocabulary."""

import unicodedata
from typing import NamedTuple

from .text_quality import _is_base, _is_mark, _require_text
from .tools import get_khmer_dictionary


class TokenSpan(NamedTuple):
    text: str
    start: int
    end: int
    kind: str


def _boundary(text, position):
    """Avoid cuts immediately before marks/joiners or inside a coeng sequence."""
    if position < len(text) and (_is_mark(text[position]) or text[position] in "\u200c\u200d"):
        return False
    previous = position - 1
    while previous >= 0 and text[previous] in "\u200c\u200d":
        previous -= 1
    return previous < 0 or text[previous] != "\u17d2"


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


def khseg_spans(text, custom_words=None):
    """Segment without changing or discarding any source character.

    Add domain vocabulary with an iterable of nonempty strings. Longest exact
    matches win; unknown Khmer runs stop before the next recognized word at a
    safe structural boundary. ``kind='word'`` means a dictionary match, not a
    confidence estimate. No normalization is implicit. Offsets are code points.
    """
    _require_text(text)
    dictionary = get_khmer_dictionary()
    if custom_words is not None:
        if isinstance(custom_words, (str, bytes)):
            raise TypeError("custom_words must be an iterable of nonempty strings, not a string")
        for word in custom_words:
            if not isinstance(word, str):
                raise TypeError("every custom word must be a str")
            if not word or not word.strip():
                raise ValueError("custom words must not be empty or whitespace-only")
            dictionary.add(word)

    # Prefix trie bounds lookup by candidate length, not the remaining document.
    trie = {}
    for word in dictionary:
        node = trie
        for char in word:
            node = node.setdefault(char, {})
        node[None] = True

    def longest_end(start):
        if not _boundary(text, start):
            return start
        node, position, best = trie, start, start
        while position < len(text) and text[position] in node:
            node = node[text[position]]
            position += 1
            if None in node and _boundary(text, position):
                best = position
        return best

    tokens = []
    position = 0
    while position < len(text):
        end = longest_end(position)
        if end > position:
            kind = "word"
        else:
            kind = _kind(text[position])
            end = position + 1
            if kind not in ("punctuation", "other", "boundary"):
                while end < len(text) and _kind(text[end]) == kind:
                    if longest_end(end) > end:
                        break
                    end += 1
        tokens.append(TokenSpan(text[position:end], position, end, kind))
        position = end
    return tokens
