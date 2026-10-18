# Changelog

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
