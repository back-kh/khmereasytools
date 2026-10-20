"""KET-OCR: the Khmer Easy Tools pipeline around optional local Tesseract."""
from .documents import khanalyze


def ket_ocr(path, *, pages=None, **options):
    """Read an image/PDF as text, raising actionable errors on failure.

    KET-OCR names the existing preparation/layout pipeline, not a new trained
    recognizer. Requires [ocr], Tesseract and Khmer language data. Pass
    lang='khm+eng' for mixed pages; khanalyze returns the corresponding layout.
    Other keyword options are the same as khanalyze. Inputs are unchanged.
    """
    options.setdefault("segment", False)
    return khanalyze(path, pages=pages, **options).text
