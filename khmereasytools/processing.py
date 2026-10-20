"""A single local entry point for everyday text, image and PDF preparation."""

from pathlib import Path
from typing import NamedTuple, Optional, Tuple

from .documents import DocumentLayout, khanalyze
from .extraction import TextMatch, khextract
from .segmentation import TokenSpan, khseg_spans
from .sentences import SentenceSpan, khsentences
from .text_quality import NormalizationResult, TextAudit, khaudit, khnormalize

_TEXT = frozenset((".txt", ".text", ".md", ".csv", ".tsv", ".json", ".log"))
_IMAGE = frozenset((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp", ".ppm", ".pgm", ".pbm"))


class ProcessResult(NamedTuple):
    source_type: str
    text: str
    sentences: Tuple[SentenceSpan, ...]
    tokens: Tuple[TokenSpan, ...]
    entities: Tuple[TextMatch, ...]
    audit: TextAudit
    normalization: NormalizationResult
    document: Optional[DocumentLayout]

    @property
    def original_text(self):
        return self.normalization.original


def _document_kind(path, header):
    if path.suffix.lower() in _TEXT:
        return "text"
    if path.suffix.lower() == ".pdf" or b"%PDF-" in header:
        return "pdf"
    image_header = header.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8", b"GIF87a", b"GIF89a",
                                      b"II*\0", b"MM\0*", b"II+\0", b"MM\0+", b"BM"))
    image_header = image_header or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
    return "image" if image_header or path.suffix.lower() in _IMAGE else "text"


def khprocess(path, *, pages=None, date_order=None, **ocr_options):
    """Read a local file, conservatively clean it, and return a useful report.

    UTF-8 text files need no extras. Images/PDFs reuse optional local OCR.
    Sentences, tokens and entities address report.text; normalization maps
    them to original_text. audit describes original_text before cleanup.
    Nested document boxes/offsets keep their original page-local contract.
    OCR options apply only to image/PDF input. No translation is invoked.
    """
    if date_order not in (None, "DMY", "MDY"):
        raise ValueError("date_order must be None, 'DMY', or 'MDY'")
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    with path.open("rb") as handle:
        kind = _document_kind(path, handle.read(1024))
    document = None
    if kind == "text":
        if pages is not None or ocr_options:
            raise ValueError("pages and OCR options apply only to images or PDFs")
        with path.open(encoding="utf-8", newline="") as handle:
            original = handle.read()
        if "\0" in original:
            raise ValueError("Text input must be UTF-8 without NUL bytes; convert other encodings explicitly")
    else:
        # Segment once over the combined text by default. Callers can request
        # per-line tokens explicitly through the existing segment OCR option.
        ocr_options.setdefault("segment", False)
        document = khanalyze(path, pages=pages, **ocr_options)
        original = document.text
        kind = document.source_type
    normalized = khnormalize(original)
    return ProcessResult(
        kind, normalized.text, tuple(khsentences(normalized.text, with_spans=True)),
        tuple(khseg_spans(normalized.text)), tuple(khextract(normalized.text, date_order=date_order)),
        khaudit(original), normalized, document)
