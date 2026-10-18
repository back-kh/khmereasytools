# Changelog

## 0.5.0.dev0 — unreleased

- Add reproducible real-document OCR, annotated POS, reconstructed-article sentence, and authored extraction evaluations with baseline/adapted results and explicit data-quality/training-overlap limits.
- Fix sentence splitting between consecutive initials and missed phone candidates before a sentence-ending period followed by a number.

- Add dependency-free `khsentences`, `khextract`, `khprocess`, and `khdoctor`, with daily-use CLI commands and explicit source-offset/date-ambiguity contracts.
- Extend actual image/PDF pipeline tests and installed-package validation reports with setup status, source revision, and wheel hashes.
- Add local `khindex`/`khsearch` BM25 keyword retrieval with original-text results, snippets, source-token matches, and Khmer compound recall.
- Add explicit, credentialed `khtranslate` Google Cloud Translation client and CLI; keep live provider checks separate and opt-in.
- Test fresh core/all-extras installations on Windows, macOS, and Linux, including actual Khmer OCR and khmer-nltk POS models; publish per-OS validation artifacts.
- Expand the bundled lexicon from 213 to 81,005 entries using a pinned, checksum-verified ICU adaptation under Unicode License V3.
- Make global maximum-coverage segmentation the default, with custom vocabulary and an explicit legacy compatibility mode. Token boundaries intentionally change.
- Add `khanalyze` for images and multi-page PDFs, with page-local boxes, lines/blocks/column hints, confidence, segmentation, and Khmer diagnostics.
- Extend `khocr` to PDFs while retaining its simple text return and legacy error strings.
- Add daily-use `ocr` CLI output (plain text by default), optional `--layout`, page selection, and image review overlays.
- Keep core runtime dependencies empty; combine Pillow, pytesseract, and pypdfium2 in the optional `[ocr]` extra.
- Add reproducible segmentation evaluation, data provenance, low-memory indexing, and real Khmer OCR/PDF CI tests.


## 0.4.0 — 2026-10-18

### Added

- `khaudit`: structural and Unicode review hints with source offsets, severities, and character/letter statistics.
- `khnormalize`: explicit cleanup options, reversible edit records, and per-output-character source spans.
- `khdigits`: Khmer/ASCII digit conversion preserving leading zeros and separators.
- `khseg_spans`: lossless token spans, unknown-run labels, and custom vocabulary.
- UTF-8 CLI with JSON reports, stdin/file support, and `python -m khmereasytools`.
- Regression/property-style tests and CI with wheel-install checks.

### Fixed

- Restored package code missing from GitHub using the verified 0.3.8 PyPI source archive.
- Corrected the POS dependency distribution to `khmer-nltk`; retained the `khmernltk` extra name.
- Deferred optional dependencies until use, bounded legacy dictionary searches, and closed OCR image handles.
- Replaced inaccurate README examples and documented linguistic limitations and prior art.
- Removed stale root initializer/distribution metadata; added an explicit build backend.

Legacy API signatures and segmentation/filtering behavior remain available. The new span tokenizer is opt-in and has different unknown-word behavior. No trained model, full Khmer reordering, or OCR accuracy improvement is claimed.

## 0.3.8

Published baseline. See [source provenance](docs/SOURCE_PROVENANCE.md).
