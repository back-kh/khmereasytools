"""Source-aligned extraction of common text patterns, without model downloads."""

import re
from datetime import date
from typing import NamedTuple, Optional

from .text_quality import _require_text, khdigits

_URL = re.compile(r"""(?<![A-Za-z0-9_@])(?:https?://|www\.)[^\s<>"'“”‘’។៕。？！]+""", re.IGNORECASE)
_EMAIL = re.compile(r"(?<![A-Za-z0-9_.+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_DATE = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"(?P<y>[0-9]{4})(?P<s>[-/.])(?P<m>[0-9]{1,2})(?P=s)(?P<d>[0-9]{1,2})|"
    r"(?P<a>[0-9]{1,2})(?P<t>[-/.])(?P<b>[0-9]{1,2})(?P=t)(?P<c>[0-9]{4})"
    r")(?![A-Za-z0-9])")
_PHONE = re.compile(
    r"(?<![A-Za-z0-9+])(?:\+855[ \t.-]*(?:\(0\)[ \t.-]*)?|0)"
    r"[1-9](?:[ \t.-]*[0-9]){7,8}(?![A-Za-z0-9]|[ \t-]*[0-9]|\.[0-9])")
_NUMBER = re.compile(
    r"(?<![A-Za-z0-9_.,])[-+−]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?"
    r"(?![A-Za-z0-9_]|[.,][0-9])")
_KINDS = frozenset(("url", "email", "date", "phone", "number"))


class TextMatch(NamedTuple):
    kind: str
    text: str
    start: int
    end: int
    value: Optional[str]


def _links(text):
    """Shared URL/email protection for extraction and sentence splitting."""
    for match in _URL.finditer(text):
        value = match.group()
        balance = {closing: value.count(closing) - value.count(opening)
                   for closing, opening in ((")", "("), ("]", "["), ("}", "{"))}
        end = len(value)
        while end:
            last = value[end - 1]
            if last in ".,;:!?":
                end -= 1
                continue
            if last not in balance or balance[last] <= 0:
                break
            balance[last] -= 1
            end -= 1
        value = value[:end]
        if value and value.casefold() not in ("http://", "https://", "www."):
            yield "url", match.start(), match.start() + len(value), value
    for match in _EMAIL.finditer(text):
        value = match.group()
        local, domain = value.rsplit("@", 1)
        labels = domain.split(".")
        if (len(value) <= 254 and len(local) <= 64 and not local.endswith(".")
                and ".." not in local and all(len(label) <= 63 and not label.startswith("-")
                                             and not label.endswith("-") for label in labels)):
            yield "email", match.start(), match.end(), local + "@" + domain.lower()


def _date_value(match, order):
    if match.group("y") is not None:
        return date(int(match.group("y")), int(match.group("m")), int(match.group("d"))).isoformat()
    first, second, year = (int(match.group(name)) for name in ("a", "b", "c"))
    candidates = {}
    for label, month, day in (("DMY", second, first), ("MDY", first, second)):
        try:
            candidates[label] = date(year, month, day).isoformat()
        except ValueError:
            pass
    if order is not None:
        if order not in candidates:
            raise ValueError("Invalid date for selected order")
        return candidates[order]
    values = set(candidates.values())
    if not values:
        raise ValueError("Invalid calendar date")
    return next(iter(values)) if len(values) == 1 else None


def khextract(text, *, kinds=None, date_order=None):
    """Find URLs, ASCII emails, Cambodian phone patterns, dates, and numbers.

    Offsets refer to unchanged input, including Khmer digits. Values contain
    digit-folded strings, ISO Gregorian dates, or +855 phone candidates.
    Ambiguous dates have value=None unless date_order='DMY' or 'MDY' is set.
    Pattern recognition does not verify a contact, account, or date's meaning.
    Overlaps prefer URL, email, date, phone, then number; filtering kinds is
    applied afterwards so numbers inside an email/URL are never fabricated.
    """
    _require_text(text)
    if date_order not in (None, "DMY", "MDY"):
        raise ValueError("date_order must be None, 'DMY', or 'MDY'")
    if kinds is None:
        selected = _KINDS
    else:
        if isinstance(kinds, (str, bytes)):
            raise TypeError("kinds must be an iterable of kind names, not a string")
        selected = frozenset(kinds)
        if not selected <= _KINDS:
            raise ValueError("kinds must contain url, email, date, phone, or number")
    if not selected:
        return []
    folded = khdigits(text)
    candidates = list(_links(text))
    for match in _DATE.finditer(folded):
        try:
            value = _date_value(match, date_order)
        except ValueError:
            continue
        candidates.append(("date", match.start(), match.end(), value))
    for match in _PHONE.finditer(folded):
        digits = re.sub(r"\D", "", match.group())
        if digits.startswith("855"):
            national = digits[3:].lstrip("0")
        else:
            national = digits[1:]
        candidates.append(("phone", match.start(), match.end(), "+855" + national))
    for match in _NUMBER.finditer(folded):
        value = match.group().replace(",", "").replace("−", "-")
        candidates.append(("number", match.start(), match.end(), value))
    priority = {kind: position for position, kind in enumerate(("url", "email", "date", "phone", "number"))}
    candidates.sort(key=lambda item: (priority[item[0]], item[1], -item[2]))
    occupied = bytearray(len(text))
    result = []
    for kind, start, end, value in candidates:
        if occupied.find(b"\1", start, end) != -1:
            continue
        occupied[start:end] = b"\1" * (end - start)
        if kind in selected:
            result.append(TextMatch(kind, text[start:end], start, end, value))
    result.sort(key=lambda item: (item.start, item.end))
    return result
