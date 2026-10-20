"""A single daily-use entry point for local image and PDF OCR/layout."""

import math
import tempfile
import threading
from pathlib import Path
from typing import NamedTuple, Optional, Tuple

from .ocr import OCRError, PageLayout, _finite_number, _integer, khocr_layout

# PDFium forbids concurrent native calls, including on separate documents.
# This lock covers this module's PDFium calls; external PDFium callers must
# provide their own process-wide coordination. OCR itself runs outside it.
_PDF_LOCK = threading.RLock()


class DocumentPage(NamedTuple):
    number: int
    width_points: Optional[float]
    height_points: Optional[float]
    dpi: Optional[float]
    layout: PageLayout


class DocumentLayout(NamedTuple):
    source_type: str
    page_count: int
    pages: Tuple[DocumentPage, ...]
    text: str


def _selected_pages(pages, count):
    if pages is None:
        return list(range(1, count + 1))
    if isinstance(pages, (str, bytes)):
        raise TypeError("pages must be an iterable of 1-based page numbers")
    result = [_integer(page, "page number", 1) for page in pages]
    if not result or len(result) != len(set(result)) or any(page > count for page in result):
        raise ValueError("pages must be nonempty, unique, and inside the document")
    return result


def khanalyze(path, *, pages=None, dpi=200, password=None, **ocr_options):
    """Analyze an image or PDF with ordinary defaults and no network calls.

    PDF pages are rendered and OCRed one at a time; only text/layout is kept.
    pages selects 1-based pages in the requested order. Page-local offsets
    target page.layout.text. Document text joins pages with LF + form feed + LF.
    Boxes are top-left-origin pixels in the upright rendered page. PDF page
    sizes are also supplied in points (72 points/inch) for coordinate conversion.
    All selected PDF pages are OCRed, including PDFs with embedded text.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    with path.open("rb") as handle:
        header = handle.read(1024)
    is_pdf = path.suffix.lower() == ".pdf" or b"%PDF-" in header
    if not is_pdf:
        if pages is not None and _selected_pages(pages, 1) != [1]:
            raise ValueError("An image is analyzed as one page; use frame for a TIFF frame")
        result = khocr_layout(path, **ocr_options)
        return DocumentLayout("image", 1, (DocumentPage(1, None, None, None, result),), result.text)
    if "frame" in ocr_options:
        raise ValueError("Use pages for PDFs; frame is an image-only option")
    dpi = _finite_number(dpi, "dpi", 36, 600)
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise ImportError("Install image/PDF support with: pip install 'khmereasytools[ocr]'") from exc
    document = None
    try:
        with _PDF_LOCK:
            document = pdfium.PdfDocument(str(path), password=password)
            count = len(document)
            selected = _selected_pages(pages, count)
        results = []
        with tempfile.TemporaryDirectory(prefix="khmereasytools-pdf-") as directory:
            image_path = Path(directory) / "page.png"
            for number in selected:
                # Native PDFium objects and shared-memory PIL bitmaps are
                # fully released before OCR; the next page reuses this file.
                with _PDF_LOCK:
                    page = document[number - 1]
                    bitmap = None
                    try:
                        width, height = page.get_size()
                        render_width = math.ceil(width * dpi / 72)
                        render_height = math.ceil(height * dpi / 72)
                        if render_width * render_height > 40000000:
                            raise ValueError("Rendered PDF page exceeds 40 million pixels; lower dpi")
                        bitmap = page.render(scale=dpi / 72)
                        image = bitmap.to_pil()
                        try:
                            image.save(image_path)
                        finally:
                            image.close()
                    finally:
                        if bitmap is not None:
                            bitmap.close()
                        page.close()
                layout = khocr_layout(image_path, **ocr_options)
                results.append(DocumentPage(number, float(width), float(height), dpi, layout))
        return DocumentLayout("pdf", count, tuple(results), "\n\f\n".join(page.layout.text for page in results))
    except pdfium.PdfiumError as exc:
        raise OCRError("Could not read PDF: {}".format(exc)) from exc
    finally:
        if document is not None:
            with _PDF_LOCK:
                document.close()
