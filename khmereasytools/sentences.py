"""Conservative Khmer/mixed-text sentence rules with original source offsets."""

import re
from typing import NamedTuple

from .extraction import _links
from .text_quality import _require_text

_END = frozenset(".!?។៕。？！‼⁇⁈⁉")
_CLOSE = frozenset("\"'”’»›)]}")
_ABBREVIATION = re.compile(
    r"(?<![A-Za-z])(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc)\."
    r"|(?<![A-Za-z])(?:[A-Za-z]\.){2,}"
    r"|(?:[\u1780-\u17a2]\.){2,}|។ល។", re.IGNORECASE)
_INITIAL = re.compile(r"(?<![A-Za-z])[A-Z]\.(?=[ \t]+[A-Z][a-z])")
_NUMBER_LABEL = re.compile(r"(?<![A-Za-z])No\.(?=[ \t]*[0-9០-៩])", re.IGNORECASE)
_LINE = re.compile(r"\r\n|\r|\n|\f|\u2028|\u2029")


class SentenceSpan(NamedTuple):
    text: str
    start: int
    end: int


def khsentences(text, *, with_spans=False):
    """Split everyday Khmer/mixed text into trimmed sentences or source spans.

    Sentence punctuation, blank lines, form feeds and paragraph separators
    end a segment. Single wrapped newlines stay inside a sentence. Decimal
    points, links, common abbreviations and initials are protected. This is
    a documented heuristic, not full Unicode UAX #29 conformance or a model.
    """
    _require_text(text)
    if not isinstance(with_spans, bool):
        raise TypeError("with_spans must be a bool")
    protected = bytearray(len(text))
    for _, start, end, _ in _links(text):
        protected[start:end] = b"\1" * (end - start)
    for pattern in (_ABBREVIATION, _INITIAL, _NUMBER_LABEL):
        for match in pattern.finditer(text):
            protected[match.start():match.end()] = b"\1" * len(match.group())
    hard = set()
    previous = None
    for match in _LINE.finditer(text):
        if match.group() in ("\f", "\u2029"):
            hard.add(match.start())
        elif previous is not None and not text[previous:match.start()].strip():
            hard.add(match.start())
        previous = match.end()
    spans, start, position = [], 0, 0

    def append(end):
        nonlocal start
        left, right = start, end
        while left < right and text[left].isspace():
            left += 1
        while right > left and text[right - 1].isspace():
            right -= 1
        if left < right:
            spans.append(SentenceSpan(text[left:right], left, right))
        start = end

    while position < len(text):
        if position in hard:
            append(position)
        char = text[position]
        if char not in _END or protected[position]:
            position += 1
            continue
        if char == ".":
            before = text[position - 1] if position else ""
            after = text[position + 1] if position + 1 < len(text) else ""
            if before.isdecimal() and after.isdecimal():
                position += 1
                continue
            if before.isalnum() and after in "abcdefghijklmnopqrstuvwxyz" and after:
                position += 1
                continue
        end = position + 1
        while end < len(text) and not protected[end] and (text[end] in _END or text[end] in _CLOSE):
            end += 1
        append(end)
        position = end
    append(len(text))
    return spans if with_spans else [span.text for span in spans]
