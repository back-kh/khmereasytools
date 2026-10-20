# Changelog

## 0.5.0.dev0 — unreleased

- Maintain KET-Tagger source/training in `back-kh/ket-tagger` while preserving its bundled API, model and zero runtime dependencies. Record the component source commit and checksums, with offline CI verification and explicit synchronization safeguards.
- Improve KET-Tagger with a 239 KiB supervised khPOS CRF and pure-Python inference; retain `model="rules"`. Bundle corpus-derived weights/counts under separate CC BY-NC-SA 4.0 research licensing; software code stays MIT.
- Purge normalized CLOSE/OPEN/ALT test matches before training and freeze development-only model selection. The same ALT coarse diagnostic rises from 37.61% to 81.07%; reserved khPOS native gold-boundary accuracy is 95.94%, with 87.78% joint native F1 from unsegmented text. Preserve earlier results and adapted role-interface evidence.
- Add dependency-free KET-Tagger (`khtag`, `KhmerTagger`): authored Khmer POS/particle rules, Khmer labels, source spans, alternatives, explanations, local vocabulary, and `tag`/`ket-tagger` CLI commands. Keep unknowns visible and retain the optional CRF for broader coverage.
- Evaluate KET-Tagger on all 1,018 ALT test sentences with explicit abstention denominators and a lossy coarse-label mapping; retain the unmet compound-boundary challenge rather than claiming general POS accuracy.
- Add simple `KhmerRAG`/`khrag` with local BM25 passage retrieval, source offsets and optional explicit answer generation; no embeddings or vector database.
- Add a standard-library `LocalModel` Ollama client shared by optional local translation and RAG, with bounded responses and no automatic downloads or cloud fallback. Translation remains a functional interface without a quality evaluation.
- Name the existing Tesseract-based image/PDF pipeline KET-OCR; add `ket_ocr` with exception-based errors and a `ket-ocr` CLI alias.
- Complete the KH-FUNSD comparison with five systems on 146 images and both Qwen profiles on the same 30 images; disclose the unreviewed Codex operational references and retain all failures/caps.
- Add audited whitespace-unit/segmentation-assisted WER and historical S/D/I/serialization diagnostics without changing frozen CER or suppressing repetitive output.
- Reject empty local-model CLI selections and incomplete local setup before any cloud translation call.

- Measure the sub-10% OCR target with pinned fast/best models and native installed image/PDF checks; retain the lightweight default when the larger model does not improve the comparison. Document swapped development image/transcript pairings without altering historical raw scores.

- Improve default segmentation with 16,546 pinned SIL NRSI unigram counts while retaining the 81,005-entry vocabulary and zero core dependencies; preserve explicit coverage/longest/legacy modes.
- Tag chosen POS words directly with the existing optional CRF, avoiding whitespace tokens and loading of a second model; serialize native tagger access.
- Share bounded automatic small-image OCR preprocessing across plain, structured, PDF and CLI paths, mapping boxes back to source coordinates; retain explicit no-preprocessing mode.
- Add paired, whole-word POS/segmentation and real-document OCR accuracy checks on fresh native Windows/macOS/Linux wheel installs, with a corrected NOVA compound adapter and explicit evaluation limits.

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
