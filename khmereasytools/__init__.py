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
from .documents import DocumentLayout, DocumentPage, khanalyze
from .lexicon import get_khmer_dictionary
from .segmentation import TokenSpan, khseg_spans
from .search import KhmerSearchIndex, SearchHit, SearchMatch, khindex, khsearch
from .translation import TranslationError, khtranslate
from .sentences import SentenceSpan, khsentences
from .extraction import TextMatch, khextract
from .processing import ProcessResult, khprocess
from .diagnostics import DoctorCheck, DoctorReport, khdoctor
from .ocr import (Box, LayoutColumn, OCRBlock, OCRError, OCRLine, OCRWord, PageLayout,
                  khlayout, khocr_layout, khocr_overlay)
from .text_quality import (
    NormalizationResult,
    TextAudit,
    TextEdit,
    TextIssue,
    khaudit,
    khdigits,
    khnormalize,
)

__version__ = "0.5.0.dev0"

__all__ = [
    "get_default_stop_words", "load_stop_words_from_file", "khfilter", "khseg",
    "khsyllable", "khpos", "khocr", "is_khmer", "khseg_spans", "khaudit",
    "khdigits", "khnormalize", "TokenSpan", "TextIssue", "TextAudit", "TextEdit",
    "NormalizationResult", "__version__", "get_khmer_dictionary",
    "Box", "LayoutColumn", "OCRBlock", "OCRError", "OCRLine", "OCRWord",
    "PageLayout", "khlayout", "khocr_layout", "khocr_overlay",
    "DocumentLayout", "DocumentPage", "khanalyze",
    "KhmerSearchIndex", "SearchHit", "SearchMatch", "khindex", "khsearch",
    "TranslationError", "khtranslate",
    "SentenceSpan", "khsentences", "TextMatch", "khextract",
    "ProcessResult", "khprocess", "DoctorCheck", "DoctorReport", "khdoctor",
]
