"""Optional Tesseract OCR, text geometry, and heuristic reading-order analysis.

Coordinates use pixels in the EXIF-transposed input image. Text offsets refer
only to the reconstructed OCR text, not to bytes or characters in the image.
"""

import math
from collections import OrderedDict
from pathlib import Path
from typing import NamedTuple, Optional, Tuple

from .segmentation import TokenSpan, khseg_spans
from .text_quality import TextAudit, khaudit


class OCRError(RuntimeError):
    """An OCR engine, language-data, or timeout failure."""


class Box(NamedTuple):
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height


class OCRWord(NamedTuple):
    text: str
    confidence: float
    box: Box
    block_id: int
    paragraph_id: int
    line_id: int


class OCRLine(NamedTuple):
    id: Tuple[int, int, int]
    text: str
    start: int
    end: int
    box: Box
    word_indices: Tuple[int, ...]
    confidence: Optional[float]
    column: Optional[int]
    tokens: Tuple[TokenSpan, ...]


class OCRBlock(NamedTuple):
    id: int
    box: Box
    line_indices: Tuple[int, ...]


class LayoutColumn(NamedTuple):
    box: Box
    line_indices: Tuple[int, ...]


class PageLayout(NamedTuple):
    width: int
    height: int
    text: str
    words: Tuple[OCRWord, ...]
    lines: Tuple[OCRLine, ...]
    blocks: Tuple[OCRBlock, ...]
    columns: Tuple[LayoutColumn, ...]
    confidence: Optional[float]
    audit: TextAudit
    filtered_word_count: int
    engine: str
    language: str
    reading_order: str
    warnings: Tuple[str, ...]


def _union(boxes):
    left = min(box.left for box in boxes)
    top = min(box.top for box in boxes)
    right = max(box.right for box in boxes)
    bottom = max(box.bottom for box in boxes)
    return Box(left, top, right - left, bottom - top)


def _confidence(words):
    weight = sum(len(word.text) for word in words)
    return sum(len(word.text) * word.confidence for word in words) / weight if weight else None


def _finite_number(value, name, minimum, maximum=None):
    if isinstance(value, bool):
        raise ValueError(name + " must be a finite number")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(name + " must be a finite number")
    if not math.isfinite(number) or number < minimum or (maximum is not None and number > maximum):
        raise ValueError(name + " is outside its permitted range")
    return number


def _integer(value, name, minimum=0):
    number = _finite_number(value, name, minimum)
    if int(number) != number:
        raise ValueError(name + " must be an integer")
    return int(number)


def _columns(boxes, page_width):
    """Find separated x-intervals, excluding lines spanning most of the page.

    Wide lines remain unassigned when they overlap multiple columns. This is
    a geometric hint, not a semantic table/heading/figure classifier.
    """
    intervals = sorted((box.left, box.right) for box in boxes if box.width < 0.7 * page_width)
    groups = []
    for left, right in intervals:
        if groups and left - groups[-1][1] < 0.04 * page_width:
            groups[-1][1] = max(groups[-1][1], right)
        else:
            groups.append([left, right])
    if len(groups) < 2:
        return [0] * len(boxes)
    assignment = []
    for box in boxes:
        overlaps = [max(0, min(box.right, right) - max(box.left, left)) for left, right in groups]
        touched = [index for index, overlap in enumerate(overlaps) if overlap > 0]
        assignment.append(touched[0] if len(touched) == 1 else None)
    # Renumber only occupied columns from left to right.
    mapping = {old: new for new, old in enumerate(sorted({c for c in assignment if c is not None}))}
    return [mapping.get(column) for column in assignment]


def _reading_order(boxes, assignment):
    spanning = sorted((i for i, column in enumerate(assignment) if column is None),
                      key=lambda i: (boxes[i].top, boxes[i].left, i))
    remaining = set(range(len(boxes))) - set(spanning)
    order = []
    for span in spanning + [None]:
        limit = boxes[span].top if span is not None else math.inf
        band = [i for i in remaining if boxes[i].top < limit]
        order.extend(sorted(band, key=lambda i: (assignment[i], boxes[i].top, boxes[i].left, i)))
        remaining.difference_update(band)
        if span is not None:
            order.append(span)
    return order


def khlayout(data, width, height, *, min_confidence=0.0, reading_order="engine",
             segment=True, language="khm", engine="provided_tsv"):
    """Analyze one page of Tesseract image_to_data(Output.DICT) output.

    No OCR dependencies are required for this function. Only level-5 word rows
    are used. Confidence is the engine's 0..100 score, not a calibrated chance
    of correctness. Blank pages have confidence=None. The page's text inserts
    spaces between OCR words and LF between lines; token offsets target that
    reconstructed text. Column order is an explicit geometric heuristic.
    """
    width, height = _integer(width, "width", 1), _integer(height, "height", 1)
    min_confidence = _finite_number(min_confidence, "min_confidence", 0, 100)
    if reading_order not in ("engine", "columns"):
        raise ValueError("reading_order must be 'engine' or 'columns'")
    required = ("level", "text", "conf", "left", "top", "width", "height",
                "block_num", "par_num", "line_num", "page_num")
    if not isinstance(data, dict) or any(key not in data for key in required):
        raise ValueError("data must contain Tesseract word, geometry, confidence, and hierarchy columns")
    try:
        count = len(data["text"])
        if any(len(data[key]) != count or isinstance(data[key], (str, bytes)) for key in required):
            raise ValueError("all TSV columns must be equally sized sequences")
    except TypeError:
        raise ValueError("all TSV columns must be equally sized sequences")
    words, groups, pages = [], OrderedDict(), set()
    filtered = 0
    for row in range(count):
        if _integer(data["level"][row], "level", 1) != 5:
            continue
        text = data["text"][row]
        if not isinstance(text, str):
            raise ValueError("OCR text values must be strings")
        text = text.strip()
        if not text:
            continue
        page = _integer(data["page_num"][row], "page_num", 1)
        pages.add(page)
        if len(pages) > 1:
            raise ValueError("khlayout accepts one page; split multi-page TSV data by page_num")
        # -1 means unscored in Tesseract; do not pretend it is a measured 0.
        confidence = _finite_number(data["conf"][row], "word confidence", -1, 100)
        if confidence < min_confidence:
            filtered += 1
            continue
        box = Box(*(_integer(data[key][row], key) for key in ("left", "top", "width", "height")))
        if not box.width or not box.height or box.right > width or box.bottom > height:
            raise ValueError("word boxes must be nonempty and inside the page")
        identity = tuple(_integer(data[key][row], key, 1) for key in ("block_num", "par_num", "line_num"))
        groups.setdefault(identity, []).append(len(words))
        words.append(OCRWord(text, confidence, box, *identity))

    identities = list(groups)
    line_boxes = [_union([words[i].box for i in groups[key]]) for key in identities]
    assignments = _columns(line_boxes, width)
    order = list(range(len(identities))) if reading_order == "engine" else _reading_order(line_boxes, assignments)
    lines, text_parts, position = [], [], 0
    for old_index in order:
        identity = identities[old_index]
        indices = groups[identity]
        text = " ".join(words[i].text for i in indices)
        tokens = tuple(TokenSpan(token.text, token.start + position, token.end + position, token.kind)
                       for token in khseg_spans(text)) if segment else ()
        lines.append(OCRLine(identity, text, position, position + len(text), line_boxes[old_index],
                             tuple(indices), _confidence([words[i] for i in indices]),
                             assignments[old_index], tokens))
        text_parts.append(text)
        position += len(text) + 1
    text = "\n".join(text_parts)
    block_groups, column_groups = OrderedDict(), OrderedDict()
    for index, line in enumerate(lines):
        block_groups.setdefault(line.id[0], []).append(index)
        if line.column is not None:
            column_groups.setdefault(line.column, []).append(index)
    blocks = tuple(OCRBlock(key, _union([lines[i].box for i in indices]), tuple(indices))
                   for key, indices in block_groups.items())
    columns = tuple(LayoutColumn(_union([lines[i].box for i in column_groups[key]]), tuple(column_groups[key]))
                    for key in sorted(column_groups))
    warnings = ["Columns are geometric hints; tables, figures, handwriting, and semantic roles are not classified."]
    if filtered:
        warnings.append("{} unscored or below-threshold OCR words were excluded.".format(filtered))
    return PageLayout(width, height, text, tuple(words), tuple(lines), blocks, columns,
                      _confidence(words), khaudit(text), filtered, engine, language,
                      reading_order, tuple(warnings))


def _dependencies():
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise ImportError("Install OCR dependencies with: pip install 'khmereasytools[ocr]'") from exc
    return pytesseract, Image, ImageOps


def khocr_layout(image_path, *, lang="khm", psm=3, timeout=60.0, min_confidence=0.0,
                 preprocess="none", reading_order="engine", segment=True, frame=0):
    """OCR a page image or a selected TIFF frame, then analyze its text layout.

    Supports PNG/JPEG and other Pillow raster formats; PDF must first be
    rasterized. EXIF orientation is honored. Preprocessing never resizes the
    image, so boxes use upright-image pixels. This API raises errors rather
    than returning an error string. No file or document is uploaded anywhere.
    """
    if not isinstance(lang, str) or not lang or any(not part or not all(c.isalnum() or c in "_/" for c in part) for part in lang.split("+")):
        raise ValueError("lang must contain Tesseract language names joined by +")
    psm = _integer(psm, "psm", 1)
    if psm not in (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
        raise ValueError("psm must select a Tesseract mode that performs OCR (1 or 3..13)")
    timeout = _finite_number(timeout, "timeout", 0)
    if timeout == 0:
        raise ValueError("timeout must be greater than zero")
    frame = _integer(frame, "frame")
    min_confidence = _finite_number(min_confidence, "min_confidence", 0, 100)
    if preprocess not in ("none", "grayscale", "threshold"):
        raise ValueError("preprocess must be 'none', 'grayscale', or 'threshold'")
    if reading_order not in ("engine", "columns"):
        raise ValueError("reading_order must be 'engine' or 'columns'")
    pytesseract, Image, ImageOps = _dependencies()
    try:
        available = set(pytesseract.get_languages(config=""))
        missing = set(lang.split("+")) - available
        if missing:
            raise OCRError("Missing Tesseract language data: {}. Install the matching traineddata.".format(", ".join(sorted(missing))))
        with Image.open(image_path) as original:
            try:
                original.seek(frame)
            except EOFError as exc:
                raise ValueError("frame is outside this image's available frames") from exc
            upright = ImageOps.exif_transpose(original)
            # Composite transparency on white; transparent black is not ink.
            if upright.mode in ("RGBA", "LA") or (upright.mode == "P" and "transparency" in upright.info):
                rgba = upright.convert("RGBA")
                page = Image.new("RGB", rgba.size, "white")
                page.paste(rgba, mask=rgba.getchannel("A"))
            else:
                page = upright.convert("RGB")
            width, height = page.size
            if preprocess != "none":
                page = ImageOps.autocontrast(ImageOps.grayscale(page))
                if preprocess == "threshold":
                    page = page.point(lambda value: 255 if value >= 128 else 0)
            data = pytesseract.image_to_data(page, lang=lang, config="--psm {}".format(psm),
                                            output_type=pytesseract.Output.DICT, timeout=timeout)
        return khlayout(data, width, height, min_confidence=min_confidence,
                        reading_order=reading_order, segment=segment, language=lang,
                        engine="tesseract")
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRError("Tesseract is not installed or not on PATH; install the engine and khm traineddata.") from exc
    except pytesseract.TesseractError as exc:
        raise OCRError("Tesseract failed: {}".format(exc)) from exc
    except RuntimeError as exc:
        if isinstance(exc, OCRError):
            raise
        raise OCRError("OCR timed out or the engine failed: {}".format(exc)) from exc


def khocr_overlay(image_path, layout, output_path, *, level="line", frame=0):
    """Save a review image with text-region rectangles; source stays untouched."""
    if level not in ("word", "line", "block", "column"):
        raise ValueError("level must be 'word', 'line', 'block', or 'column'")
    if Path(image_path).resolve() == Path(output_path).resolve():
        raise ValueError("overlay output must differ from the source image")
    _, Image, ImageOps = _dependencies()
    from PIL import ImageDraw
    with Image.open(image_path) as original:
        original.seek(_integer(frame, "frame"))
        page = ImageOps.exif_transpose(original).convert("RGB")
    if page.size != (layout.width, layout.height):
        raise ValueError("layout dimensions do not match the upright source image")
    elements = {"word": layout.words, "line": layout.lines,
                "block": layout.blocks, "column": layout.columns}[level]
    draw = ImageDraw.Draw(page)
    colors = ("#d12525", "#155fc7", "#168044", "#8c37b5")
    for index, element in enumerate(elements):
        box = element.box
        color = colors[index % len(colors)]
        draw.rectangle((box.left, box.top, box.right - 1, box.bottom - 1), outline=color, width=2)
        draw.text((box.left + 2, box.top + 2), str(index), fill=color)
    page.save(output_path)
    return str(output_path)
