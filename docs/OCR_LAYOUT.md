# Image and PDF OCR/layout

Daily use needs only `khocr(file)` for text or `khanalyze(file)` for text plus layout. Both accept images and PDFs. Core text tools remain independent of all optional packages.

## Setup and default behavior

Install `khmereasytools[ocr]` (or `.[ocr]` from this development checkout), the Tesseract executable, and `khm` traineddata. Pillow reads raster formats, pytesseract invokes the local engine, and pypdfium2 renders PDFs. No image/document leaves the machine. These dependencies are loaded lazily; plain image OCR does not load the expanded segmentation lexicon.

PDF pages render at 200 DPI by default and are processed one at a time. The selected page results contain text and geometry; rendered images are removed with the temporary directory on success or failure. Pages with embedded text are also OCRed: there is no automatic native-text extraction switch. This avoids separate behavior for scanned versus text PDFs but may introduce recognition errors into an otherwise correct text PDF.

`khanalyze(path, pages=[1, 3])` selects 1-based PDF pages in that order. `password=` can unlock an encrypted PDF and is not stored in the report. A raster image produces one page; `frame=` selects a frame from a multi-frame TIFF. Large rendered pages are rejected above 40 million pixels; `dpi=` can lower their size.

## Reports

`DocumentLayout` has `source_type`, original `page_count`, selected `pages`, and combined `text`. Each `DocumentPage` has a 1-based `number`, optional PDF `width_points`/`height_points`/`dpi`, and a `PageLayout`:

- `words`: recognized strings, engine confidence, pixel boxes, and Tesseract hierarchy IDs.
- `lines`: reconstructed text, box, word indices, confidence, page-text start/end, optional column index, and segmentation tokens.
- `blocks`: text blocks with boxes and line indices.
- `columns`: geometric column hints with boxes and line indices.
- `audit`: Khmer letter statistics and structural text concerns.
- `filtered_word_count`: unscored/below-threshold words excluded from this report.

Text is reconstructed with spaces between engine words and LF between lines. Combined document text joins pages with `\n\f\n`. Page token/audit offsets refer to that page's reconstructed text, not to document-global text or the original image. Images have no exact source character offsets.

Boxes use top-left-origin pixels in the upright, EXIF-transposed image or rendered PDF page. For a rendered PDF page, multiply x coordinates by `width_points / layout.width` and y coordinates by `height_points / layout.height` to obtain top-left-origin point coordinates in its displayed page. A PDF API expecting bottom-left coordinates needs an additional y-axis conversion. Rotation/crop handling follows the renderer's displayed page.

## Optional controls

`khanalyze` forwards OCR options such as `lang="khm+eng"`, `psm=6` (single text block), `timeout=60`, `min_confidence=50`, `preprocess="grayscale"`, `reading_order="columns"`, and `segment=False`. Defaults use `khm`, automatic page segmentation, all scored words, `preprocess="auto"`, engine reading order, and text diagnostics/segmentation. Auto mode uses grayscale/autocontrast and 2x enlargement when the longest edge is below 1600 pixels, mapping boxes outward to original source pixels. Larger images keep the previous pixel path. `preprocess="none"` disables enlargement; explicit grayscale/threshold retain their previous meanings. `khocr_layout(image)` provides the same page analysis for image callers; `khlayout` analyzes existing engine data without OCR dependencies.

Column inference merges horizontally overlapping line intervals, ignoring near-full-width lines. Optional column reading order divides the page around spanning lines, then reads columns left to right and lines top to bottom within each band. It is a heuristic and can fail with tables, inset text, ragged columns, sidebars, or complex overlapping layouts. Engine order is the default. No heading/table/figure/handwriting classifier is included.

Confidence is Tesseract's engine score, not a calibrated probability. Page/line scores are weighted by recognized code-point count. Blank pages have `confidence=None`, empty text, and no fabricated boxes. Text below an explicit threshold is counted as filtered; no spelling/OCR repair is guessed.

`khocr_overlay(image, page_layout, "review.png")` draws review boxes without overwriting the input. `level=` selects words, lines, blocks, or columns. CLI `--overlay` currently supports image inputs; PDF coordinates are available through `--layout`.

The new analysis APIs raise actionable exceptions. `khocr` retains the legacy error-string behavior for compatibility. OCR dependency failures mention the optional extra; missing engine/language data, invalid pages, malformed geometry, and timeouts are reported explicitly. PDFium's native calls inside the library are serialized; external PDFium users must also coordinate native calls if using threads.

## Validation and limits

A bundled synthetic four-line Khmer page and a two-page PDF exercise real Tesseract recognition, language data, page selection, coordinate bounds, CLI output, and overlays. The local clean fixture was recognized correctly with PSM 6. Default automatic segmentation can still introduce errors on the same PDF. These are integration fixtures, **not** estimates of real-world OCR character error rate or layout quality.

Further evaluation needs independently transcribed real scans, varied fonts and resolution, rotated/noisy pages, and annotated multi-column layouts. OCR analysis does not add an accuracy-trained OCR model. The local engine and traineddata determine recognition behavior.

[Paired accuracy checks](IMPROVEMENTS.md) reduce image CER from 15.99% to
11.43% on the 40-page reserved partition locally. The [historical baseline](ACCURACY.md)
also records all 60 images and 15 derived PDF pages under the earlier pixel
path. Annotation alignment problems limit crop/layout diagnostics; semantic
layout quality is not established. khocr now shares the structured recognition
path, so whitespace formatting may differ from its earlier image_to_string path.

Sources: [Tesseract TSV and CLI documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [pytesseract API](https://github.com/madmaze/pytesseract), and [pypdfium2 API and thread-safety guidance](https://pypdfium2.readthedocs.io/en/stable/python_api.html).
