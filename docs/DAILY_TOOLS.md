# Everyday text and file tools

These four tools are part of the unreleased 0.5 source version. Sentence splitting, extraction, UTF-8 text processing, and setup diagnostics use only the Python standard library. Image/PDF processing reuses the optional OCR backend. No input file is overwritten and no translation is invoked by these tools.

## Split sentences

```python
from khmereasytools import khsentences

sentences = khsentences("សួស្តី។ ខ្ញុំអានសៀវភៅ។")
assert sentences == ["សួស្តី។", "ខ្ញុំអានសៀវភៅ។"]

for sentence in khsentences("  សួស្តី។ បន្ទាប់។", with_spans=True):
    print(sentence.text, sentence.start, sentence.end)
```

The default result is a list of trimmed strings. `with_spans=True` returns `SentenceSpan(text, start, end)` records. Offsets are original Python code points with exclusive ends. Separating whitespace is omitted; every non-whitespace character is retained in a source span. Single wrapped newlines remain inside a sentence; blank lines, form feeds, and paragraph separators end a segment. CRLF counts as one line break.

The heuristic recognizes Khmer `។`/`៕`, common Latin/fullwidth sentence punctuation, repeated terminal punctuation, and closing quotes/brackets. It protects decimals (including Khmer digits), URLs/emails, Latin initial abbreviations, selected English titles, Khmer multi-initial abbreviations such as `គ.ស.`, and `។ល។`. It does not infer sentence boundaries from ordinary spaces. Abbreviations can still hide a real sentence ending, and missing punctuation can join sentences.

This is an explicitly limited rule set, informed by [Unicode sentence-boundary guidance](https://www.unicode.org/reports/tr29/) and the [Khmer script description](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-16/). It does not implement all UAX #29 rules/property tables and claims no full Unicode segmentation conformance or measured linguistic accuracy.

```bash
khmereasytools sentences notes.txt
```

The CLI emits JSON sentence spans; input may also come from UTF-8 stdin.

## Extract common patterns

```python
from khmereasytools import khextract

matches = khextract("លេខ០១២ ៣៤៥ ៦៧៨ ថ្ងៃ១៨/១០/២០២៦")
for item in matches:
    print(item.kind, item.text, item.value, item.start, item.end)

# Leave an ambiguous date unresolved, or choose the order explicitly.
assert khextract("01/02/2026")[0].value is None
assert khextract("01/02/2026", date_order="DMY")[0].value == "2026-02-01"
```

`TextMatch` contains `kind`, unchanged source `text`, `start`, exclusive `end`, and normalized `value`. `kinds=["email", "phone"]` filters returned types. Recognized kinds are:

| Kind | Supported patterns and value |
| --- | --- |
| `url` | Common HTTP(S) and `www.` links; keep the source URL and trim surrounding sentence punctuation/unbalanced closing brackets |
| `email` | Common ASCII email syntax; preserve local-part case and lowercase the domain; not full RFC mailbox validation |
| `phone` | Cambodian-style domestic 9/10-digit numbers and `+855` forms, with common separators/optional `(0)`; normalize to a `+855` candidate |
| `date` | Numeric Gregorian dates using consistent `-`, `/`, or `.` separators; year-first dates normalize directly; year-last dates require calendar validity and leave differing DMY/MDY interpretations as `None` unless an order is supplied |
| `number` | ASCII/Khmer digits, optional sign, comma groups of three, and dot decimals; return an ASCII string preserving precision and leading zeros |

Phone recognition does not check active accounts, current operator allocations, or contact ownership. Date recognition does not convert Buddhist/lunar calendars or parse natural-language dates/timestamps. Numeric values do not infer currencies, scale percentages, or evaluate arithmetic. Other locale conventions are not guessed.

Overlapping matches prefer URL, email, date, phone, then number. Filtering happens after overlap resolution, so asking for numbers does not extract digits embedded inside a URL/contact/date. Matches are returned in source order, including original Khmer digits and exact code-point positions. No OCR/spelling repair, named-entity model, or network lookup is used.

```bash
khmereasytools extract notes.txt
khmereasytools extract notes.txt --kind phone --kind email
khmereasytools extract notes.txt --kind date --date-order DMY
```

## Process a file in one call

```python
from khmereasytools import khprocess

report = khprocess("notes.txt")
print(report.text)
print(report.original_text)
print(report.sentences, report.tokens, report.entities)

# With the optional OCR setup:
# report = khprocess("scan.jpg", lang="khm+eng")
# report = khprocess("document.pdf", pages=[2], dpi=200)
```

`ProcessResult` contains `source_type`, `text`, `sentences`, `tokens`, `entities`, `audit`, `normalization`, and optional `document`. `original_text` is a convenience property for `normalization.original`.

Text files are decoded strictly as UTF-8 with original newlines preserved before normalization. Explicit text extensions (`.txt`, `.text`, `.md`, `.csv`, `.tsv`, `.json`, `.log`) are read as text; structured markup is not parsed. Unknown extensions also use UTF-8 unless recognized image/PDF headers are present. Images/PDFs use the existing local `khanalyze` pipeline. NUL-bearing or non-UTF-8 text is rejected with an input error rather than guessed as another encoding.

Cleanup uses `khnormalize` defaults: remove leading BOMs and normalize CR/CRLF to LF. Digits, shaping controls, punctuation, spaces, and spelling remain unchanged. `audit` describes the extracted original text before cleanup. Top-level sentence, token, and entity offsets refer to `report.text`; `normalization.source_spans` maps them back to `report.original_text`.

For OCR input, nested `document` geometry and offsets keep their existing page-local meaning. It contains the original OCR text, not the cleaned combined text. The pipeline segments the combined text once by default; per-line OCR tokens can be requested explicitly with `segment=True`. All PDF pages still go through OCR, including PDFs containing embedded text. PDF/OCR options apply only to image/PDF inputs; `date_order=` controls extraction for either input type.

```bash
khmereasytools process notes.txt
khmereasytools process document.pdf --pages 1,2
khmereasytools process scan.jpg --lang khm+eng --json
```

The default output is cleaned text with no added newline. `--json` includes the full report and source mappings. `process` requires a file path; `sentences`/`extract` also accept stdin. Reports retain source text and mapping arrays, so process large collections document by document.

## Check setup

```bash
khmereasytools doctor
khmereasytools doctor --json
khmereasytools doctor --require ocr --require pdf
```

Python callers can use `khdoctor(timeout=5.0)`. The report lists `core`, `ocr`, `pdf`, `pos`, and `translation`, with status, explanation, and installation hint. The doctor checks optional package availability and, when Tesseract is on PATH, runs a bounded local `--list-langs` probe for `khm`. It does not import optional models, install packages, alter configuration, download data, perform OCR/POS tagging, or contact a translation service. Binary/model health is established by separate integration tests, not package-presence checks.

`ready` means local prerequisites were found. Translation can only be `configured` or `missing`: presence of `GOOGLE_TRANSLATE_API_KEY` is reported without exposing its value or validating it remotely. Other failures can be `missing` or `error`. Plain `doctor` exits 0 because optional features are optional; `--require` exits 2 if any requested feature is not ready/configured. Core text tools remain usable when optional features are missing.

Install only the extras needed for daily work. OCR/PDF setup requires `khmereasytools[ocr]`, Tesseract, and Khmer traineddata; POS requires `khmereasytools[khmernltk]`. The doctor prints OS-appropriate engine setup hints and never attempts privileged installation itself.
