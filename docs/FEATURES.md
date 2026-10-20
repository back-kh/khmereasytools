# Public API and daily-use guide

This catalog describes the 0.5.0.dev0 GitHub source, with **27 public
functions**. PyPI 0.4.0 is a separate, earlier release. Install from source
for this API. Unless marked optional, calls use the Python standard library
and locally bundled resources.

## Text preparation and word segmentation

| Function | Purpose | Contract and limits |
| --- | --- | --- |
| `khaudit` | Inspect Khmer marks, controls, suspicious characters and character statistics | Review hints with source positions; not spelling judgments |
| `khnormalize` | Explicit cleanup with reversible edits and per-character source mappings | Preserves spelling and Khmer character order; changes only selected formatting |
| `khdigits` | Convert Khmer/ASCII digit characters | Preserves leading zeros and separators; does not evaluate arithmetic or number words |
| `khseg` | Split Khmer text using the expanded dictionary and frequency costs | Local custom words; explicit frequency/coverage/longest/legacy strategies |
| `khseg_spans` | Lossless tokenization with offsets and token kinds | Joining returned token text reconstructs the complete input, including separators |
| `get_khmer_dictionary` | Read the bundled vocabulary | Returns an independent collection; membership is not spelling authority |
| `khfilter` | Remove stop words after segmentation | Returns joined text; it is not a keyword-ranking algorithm |
| `get_default_stop_words` | Read authored default stop words | Returns an independent set |
| `load_stop_words_from_file` | Load the first column of a UTF-8 CSV | Legacy missing-file behavior prints an error and returns an empty set |
| `is_khmer` | Check for Khmer-block characters | Presence check; not language identification or orthographic validation |
| `khsyllable` | Keep the legacy syllable helper available | Regex heuristic; no reliable linguistic syllabification claim |

[Text quality](TEXT_QUALITY.md) · [Dictionary provenance](DICTIONARY.md) ·
[Segmentation protocols and migration](EVALUATION.md).

## Tags, sentences, extraction and processing

| Function | Purpose | Contract and limits |
| --- | --- | --- |
| `khtag` | Predict Khmer POS with the compact research CRF | Offline; model is CC BY-NC-SA 4.0; fine grammar roles are heuristic |
| `khpos` | Call the existing khmer-nltk POS backend | Optional `.[khmernltk]`; preserves chosen words and custom terms |
| `khsentences` | Split sentences with source offsets when requested | Conservative punctuation/abbreviation rules, not a learned boundary model |
| `khextract` | Find common URLs, ASCII emails, Cambodian phones, numbers and numeric Gregorian dates | Pattern matches, not verified entities; ambiguous dates need an explicit date order |
| `khprocess` | Prepare one UTF-8 text file, image or PDF | Original text, cleanup mapping, tokens, sentences, extracted patterns and diagnostics; OCR setup for images/PDFs |
| `khdoctor` | Inspect installed capabilities and show setup hints | Read-only; no model download, remote credential test or automatic repair |

`KhmerTagger` reuses a tagger instance and supports local POS overrides.
`TaggedToken` includes text, offsets, POS, Khmer label, role, candidates,
decision rule and explanation. Source positions are exclusive-ended Python
code-point intervals; tagger output omits separators, while `khseg_spans`
retains them. Learned predictions are not calibrated probabilities.

[KET-Tagger](TAGGER.md) · [Daily tools](DAILY_TOOLS.md) ·
[Actual native-backend checks](VALIDATION.md).

## Search, retrieval and optional language-model clients

| Function | Purpose | Contract and limits |
| --- | --- | --- |
| `khindex` | Build a reusable local `KhmerSearchIndex` | BM25 with case/digit folding and matches inside Khmer compounds |
| `khsearch` | Search a small local document collection | Ranked results, original-source snippets and source-token positions; no semantic model |
| `khrag` | Retrieve cited passages through `KhmerRAG` | Retrieval needs no model; optional generation requires explicit setup and is unverified |
| `khtranslate` | Translate through Google or an explicitly selected local model | Functional provider interface; live translation quality is unevaluated |

`LocalModel` is the optional local HTTP client shared by translation and RAG.
It does not install a server or download weights. Google calls require your
credentials and send text to that service. Tests of HTTP/error contracts do
not establish translation or generated-answer quality.

[Search](SEARCH.md) · [KhmerRAG](RAG.md) · [Translation](TRANSLATION.md).

## Image/PDF OCR and text layout

| Function | Purpose | Contract and limits |
| --- | --- | --- |
| `ket_ocr` | Simple KET-OCR text entry point | Uses the existing Tesseract pipeline; raises exceptions on failures |
| `khocr` | Legacy-compatible plain text OCR | Accepts images/PDFs; retains legacy error-string behavior |
| `khanalyze` | Analyze a document with per-page layouts and diagnostics | Optional image/PDF dependencies and Tesseract/Khmer language data |
| `khocr_layout` | OCR an image and retain word/line/block geometry | Original upright-image coordinates; bounded auto preprocessing |
| `khlayout` | Interpret structured Tesseract text/box output | Geometric text-layout helper, not semantic heading/table classification |
| `khocr_overlay` | Draw OCR boxes for visual review | Image overlay; source image is preserved |

Install optional OCR with `python -m pip install '.[ocr]'` and install
Tesseract plus `khm` language data. PDF pages are rendered one at a time.
Use `lang="khm+eng"` explicitly for mixed Khmer/English material. Font/image
quality, reference alignment and reading order still affect accuracy.

[Setup and coordinates](OCR_LAYOUT.md) · [Paired comparisons](IMPROVEMENTS.md) ·
[CER target experiment](OCR_TARGET.md).

## Evidence and licensing

The [validation guide](VALIDATION.md) identifies installed-wheel contract
checks, optional actual backends, corpus evaluations, skipped checks and
historical revisions. The README figures use the original result files,
not new datasets. [Figure provenance](assets/README.md).

Source code/authored rules are MIT. The trained POS weights and their derived
vocabulary/counts are separately CC BY-NC-SA 4.0. Shared ICU/SIL resources
retain their own notices. [License boundaries](../MODEL_LICENSES.md).
