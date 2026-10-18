"""Conservative, inspectable text preparation; no spelling or OCR guessing.

Offsets everywhere are Python Unicode code-point offsets, with exclusive ends.
See docs/DESIGN.md for scope, Unicode references, and deliberately omitted rules.
"""

import unicodedata
from typing import NamedTuple, Tuple


_ASCII_DIGITS = "0123456789"
_KHMER_DIGITS = "០១២៣៤៥៦៧៨៩"
_TO_ASCII = str.maketrans(_KHMER_DIGITS, _ASCII_DIGITS)
_TO_KHMER = str.maketrans(_ASCII_DIGITS, _KHMER_DIGITS)
_JOIN_CONTROLS = "\u200c\u200d"
_BIDI_CONTROLS = "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
_LINE_BREAKS = "\n\r\v\f\x85\u2028\u2029"


def _require_text(text):
    if not isinstance(text, str):
        raise TypeError("text must be a str")


def _in_khmer_block(char):
    return "\u1780" <= char <= "\u17ff" or "\u19e0" <= char <= "\u19ff"


def _is_khmer(char):
    return _in_khmer_block(char) and unicodedata.category(char) != "Cn"


def _is_base(char):
    # Consonants AND independent vowels; coeng can precede either.
    return "\u1780" <= char <= "\u17b3"


def _is_mark(char):
    return _is_khmer(char) and unicodedata.category(char).startswith("M")


class TextIssue(NamedTuple):
    code: str
    severity: str
    start: int
    end: int
    text: str
    message: str


class TextAudit(NamedTuple):
    character_count: int
    khmer_character_count: int
    letter_count: int
    khmer_letter_count: int
    khmer_letter_ratio: float
    issues: Tuple[TextIssue, ...]


class TextEdit(NamedTuple):
    start: int
    end: int
    original: str
    replacement: str
    reason: str
    output_start: int
    output_end: int


class NormalizationResult(NamedTuple):
    original: str
    text: str
    edits: Tuple[TextEdit, ...]
    source_spans: Tuple[Tuple[int, int], ...]


def khdigits(text, target="ascii"):
    """Convert only ASCII/Khmer digits; retain leading zeros and separators.

    This translates characters, not numbers, currency, dates, or number words.
    Other scripts' digits are unchanged.
    """
    _require_text(text)
    if target not in ("ascii", "khmer"):
        raise ValueError("target must be 'ascii' or 'khmer'")
    return text.translate(_TO_ASCII if target == "ascii" else _TO_KHMER)


def khaudit(text):
    """Report Unicode/structural concerns without modifying the input.

    Findings are review hints, not proof of bad spelling or invalid Khmer.
    Legitimate word boundaries and shaping controls have severity 'info'.
    The letter ratio excludes marks, digits, punctuation, and whitespace.
    """
    _require_text(text)
    issues = []
    khmer_count = letter_count = khmer_letters = 0
    has_base = False

    def report(code, severity, position, message):
        issues.append(TextIssue(code, severity, position, position + 1,
                                text[position], message))

    for index, char in enumerate(text):
        category = unicodedata.category(char)
        khmer = _is_khmer(char)
        khmer_count += int(khmer)
        letter_count += int(category.startswith("L"))
        khmer_letters += int(khmer and category.startswith("L"))

        if char == "\u200b":
            report("zero_width_space", "info", index,
                   "Invisible word/line boundary; preserve unless removal is intentional.")
        elif char in _JOIN_CONTROLS:
            report("join_control", "info", index,
                   "Shaping control; removing it may change rendered text.")
        elif char == "\u2060":
            report("word_joiner", "info", index, "Invisible line-break control.")
        elif char == "\ufeff":
            report("bom", "warning", index,
                   "BOM at the start, or an embedded legacy no-break control.")
        elif char in _BIDI_CONTROLS:
            report("bidi_control", "warning", index,
                   "Bidirectional formatting control; review in mixed-script text.")
        elif char == "\ufffd":
            report("replacement_character", "warning", index,
                   "Possible earlier decoding loss; the original character is unknown.")
        elif category == "Cc" and char not in "\t\n\r":
            report("control_character", "warning", index,
                   "Unexpected control character in prose.")
        elif _in_khmer_block(char) and category == "Cn":
            report("unassigned_khmer", "warning", index,
                   "Unassigned code point in a Khmer Unicode block.")

        if char in "\u17b4\u17b5":
            report("discouraged_inherent_vowel", "warning", index,
                   "Unicode discourages these inherent-vowel characters; review before removal.")
        elif char == "\u17d8":
            report("discouraged_beyyal", "warning", index,
                   "Unicode recommends spelling out this abbreviation; no automatic replacement.")

        if char == "\u17d2":
            next_index = index + 1
            while next_index < len(text) and text[next_index] in _JOIN_CONTROLS:
                next_index += 1
            if not has_base or next_index == len(text) or not _is_base(text[next_index]):
                report("dangling_coeng", "warning", index,
                       "Coeng needs a preceding base and a following consonant/independent vowel.")
        elif _is_mark(char) and char not in "\u17b4\u17b5" and not has_base:
            report("orphan_khmer_mark", "warning", index,
                   "Khmer combining mark without a preceding Khmer base in this run.")

        if _is_mark(char) and index and char == text[index - 1]:
            report("repeated_khmer_mark", "warning", index,
                   "Adjacent identical Khmer marks; review for typing or OCR duplication.")

        if _is_base(char):
            has_base = True
        elif not _is_mark(char) and char not in _JOIN_CONTROLS:
            has_base = False

    return TextAudit(len(text), khmer_count, letter_count, khmer_letters,
                     khmer_letters / letter_count if letter_count else 0.0,
                     tuple(issues))


def khnormalize(text, *, zero_width_space="preserve", digits="preserve",
                collapse_spaces=False, strip=False, remove_bom=True,
                normalize_newlines=True, remove_inherent_vowels=False):
    """Return conservative cleanup, nonoverlapping edits, and source mappings.

    Defaults remove only a leading BOM and convert CR/CRLF to LF. Explicit
    options translate digits, handle ZWSP, collapse horizontal whitespace,
    trim edge whitespace, or remove U+17B4/U+17B5. Join controls, punctuation,
    spelling, and Khmer character ordering are always preserved.

    Every output character maps to its original half-open source span. A
    collapsed space maps to the whole source run. Edits use original offsets;
    applying their replacements from right to left reproduces ``result.text``.
    """
    _require_text(text)
    if zero_width_space not in ("preserve", "space", "remove"):
        raise ValueError("zero_width_space must be 'preserve', 'space', or 'remove'")
    if digits not in ("preserve", "ascii", "khmer"):
        raise ValueError("digits must be 'preserve', 'ascii', or 'khmer'")

    # Each piece is [replacement, original start, original end, reasons].
    pieces = []
    index = 0
    while index < len(text):
        start = index
        char = replacement = text[index]
        reasons = []
        index += 1
        if char == "\ufeff" and start == 0 and remove_bom:
            # Consume a leading run to make cleanup idempotent on repeated BOMs.
            while index < len(text) and text[index] == "\ufeff":
                index += 1
            replacement, reasons = "", ["leading_bom"]
        elif char == "\r" and normalize_newlines:
            if index < len(text) and text[index] == "\n":
                index += 1
            replacement, reasons = "\n", ["newline"]
        elif char == "\u200b" and zero_width_space != "preserve":
            replacement = " " if zero_width_space == "space" else ""
            reasons = ["zero_width_space"]
        elif char in "\u17b4\u17b5" and remove_inherent_vowels:
            replacement, reasons = "", ["inherent_vowel"]
        elif digits != "preserve":
            replacement = khdigits(char, target=digits)
            if replacement != char:
                reasons = ["digits"]
        pieces.append([replacement, start, index, reasons])

    if collapse_spaces:
        collapsed = []
        pending = []

        def flush():
            if not pending:
                return
            if any(piece[0] for piece in pending):
                reasons = list(dict.fromkeys(reason for piece in pending for reason in piece[3]))
                reasons.append("horizontal_whitespace")
                collapsed.append([" ", pending[0][1], pending[-1][2], reasons])
            else:
                collapsed.extend(pending)
            pending.clear()

        for piece in pieces:
            value = piece[0]
            if not value or (value.isspace() and value not in _LINE_BREAKS):
                pending.append(piece)
            else:
                flush()
                collapsed.append(piece)
        flush()
        pieces = collapsed

    # Deletions/edge trimming can expose another leading BOM. Handle the
    # resulting edge once so a second cleanup with the same options is stable.
    for piece in pieces:
        if not piece[0]:
            continue
        if remove_bom and piece[0] == "\ufeff":
            piece[0] = ""
            piece[3].append("leading_bom")
        elif strip and piece[0].isspace():
            piece[0] = ""
            piece[3].append("edge_whitespace")
        else:
            break
    if strip:
        for piece in reversed(pieces):
            if piece[0] and not piece[0].isspace():
                break
            if piece[0]:
                piece[0] = ""
                piece[3].append("edge_whitespace")

    output, edits, source_spans = [], [], []
    output_position = 0
    for replacement, start, end, reasons in pieces:
        output.append(replacement)
        source_spans.extend((start, end) for _ in replacement)
        if replacement != text[start:end]:
            edits.append(TextEdit(start, end, text[start:end], replacement,
                                  "+".join(reasons), output_position,
                                  output_position + len(replacement)))
        output_position += len(replacement)
    return NormalizationResult(text, "".join(output), tuple(edits), tuple(source_spans))
