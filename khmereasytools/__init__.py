"""Lightweight Khmer NLP and traceable text preparation."""

from .tools import (
    get_default_stop_words,
    load_stop_words_from_file,
    khfilter,
    khseg,
    khsyllable,
    khpos,
    khocr,
    is_khmer,
)
from .segmentation import TokenSpan, khseg_spans
from .text_quality import (
    NormalizationResult,
    TextAudit,
    TextEdit,
    TextIssue,
    khaudit,
    khdigits,
    khnormalize,
)

__version__ = "0.4.0"

__all__ = [
    "get_default_stop_words", "load_stop_words_from_file", "khfilter", "khseg",
    "khsyllable", "khpos", "khocr", "is_khmer", "khseg_spans", "khaudit",
    "khdigits", "khnormalize", "TokenSpan", "TextIssue", "TextAudit", "TextEdit",
    "NormalizationResult", "__version__",
]
