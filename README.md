# Khmer Easy Tools

Everyday Khmer tools: split words, search local text, read images or PDFs, and inspect document layouts. Core text and search tools run offline with **no runtime dependencies or model downloads**. Translation is an explicit online option with your own Google Cloud credentials.

The new **0.5.0.dev0** source version adds an **81,005-entry dictionary**, better segmentation, sentence splitting, structured extraction, one-call file processing, local search, optional translation, and setup diagnostics. PyPI 0.4.0 remains the published version until this update is released.

[Accuracy evaluation](docs/ACCURACY.md) covers 60 real document images,
15 derived PDF pages, two annotated POS corpora, and sentence/extraction
challenges. Default OCR measured 18.07% character error rate on KHOB;
segmentation plus POS measured 67.37% joint span F1 on ALT with possible
training overlap. Review the output where errors matter.

## Install

From this checkout:

```bash
# Text tools only:
python -m pip install .

# Add image and PDF reading with one optional extra:
python -m pip install '.[ocr]'
```

OCR also needs the [Tesseract engine](https://tesseract-ocr.github.io/tessdoc/Installation.html) and Khmer language data (`khm`) installed once. On Debian/Ubuntu:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-khm
```

Python 3.6+ for core features; use a maintained Python version for OCR extras. OCR/PDF support uses Pillow, pytesseract, and pypdfium2. These are imported only when needed. No OpenCV, NumPy, neural framework, or remote service is required.

Check your setup at any time:

```bash
khmereasytools doctor
```

It reports available features and installation hints. Missing optional features do not prevent core text tools from working.

## One call for everyday files

```python
import khmereasytools as ket

report = ket.khprocess("notes.txt")  # UTF-8 text; no extras needed.
# report = ket.khprocess("scan.jpg")      # Requires optional OCR setup.
# report = ket.khprocess("document.pdf")  # Same optional OCR setup.
print(report.text)
print(report.sentences)
print(report.entities)
```

The report keeps original text, conservative cleanup with source mappings, sentence/token positions, extracted patterns, and diagnostics. Images/PDFs also retain page layouts. Processing stays local and preserves input files.

```python
sentences = ket.khsentences("សួស្តី។ ខ្ញុំអានសៀវភៅ។")
assert sentences == ["សួស្តី។", "ខ្ញុំអានសៀវភៅ។"]

matches = ket.khextract("លេខ០១២ ៣៤៥ ៦៧៨ ថ្ងៃ១៨/១០/២០២៦")
assert [(item.kind, item.value) for item in matches] == [
    ("phone", "+85512345678"), ("date", "2026-10-18")]
```

Extraction covers common URLs, ASCII emails, Cambodian phone patterns, numbers, and numeric Gregorian dates. Ambiguous dates such as `01/02/2026` retain `value=None` unless you explicitly select `date_order="DMY"` or `"MDY"`. These are text patterns, not verified contacts. Sentence splitting uses conservative documented rules. See [daily tools and setup checks](docs/DAILY_TOOLS.md).

## Split Khmer words

```python
import khmereasytools as ket

assert ket.khseg("បច្ចេកវិទ្យាព័ត៌មាន") == ["បច្ចេកវិទ្យា", "ព័ត៌មាន"]
assert ket.khseg("ព្រះរាជាណាចក្រកម្ពុជា") == ["ព្រះរាជាណាចក្រ", "កម្ពុជា"]

# Add a name or domain term for this call:
words = ket.khseg("ខ្ញុំស្រឡាញ់", custom_words=["ខ្ញុំស្រឡាញ់"])
assert words == ["ខ្ញុំស្រឡាញ់"]
```

The new default considers complete candidate paths instead of committing to the first longest match. It first minimizes unknown Khmer characters, then the number of output tokens. It does not guess missing OCR characters or change spellings. Dictionary entries include compounds and phrases, so the output can still differ from your preferred word boundaries.

On the 1,000-sentence khPOS OPEN-TEST, exact-token F1 is **77.2%**, compared with **10.8%** for old `khseg` and **30.4%** for the old lossless span tokenizer. These are results on one corpus, not universal accuracy. See [evaluation protocol and limitations](docs/EVALUATION.md).

For annotations, `khseg_spans(text)` preserves every input character, including spaces and punctuation, and gives `text`, `start`, `end`, and `kind` for each token. Offsets are Python code points with exclusive ends. Custom vocabulary is local to the call.

## Search and retrieve local text

```python
documents = {
    "school": "សិស្សអានសៀវភៅនៅសាលារៀន។",
    "food": "ខ្ញុំញ៉ាំបាយ។",
}
hits = ket.khsearch("សៀវភៅ", documents)
print(hits[0].document_id, hits[0].snippet)

# Build once for repeated searches; retrieve unchanged source text by ID.
index = ket.khindex(documents)
hits = index.search("សៀវភៅ")
original = index.get("school")
```

Search ranks keyword matches using BM25, folds Latin case and Khmer/ASCII digits, and supports matches inside Khmer dictionary compounds. Results include source text, snippets, and original token positions. This is local lexical retrieval for small collections, with no semantic model or spelling correction. See [search behavior and limits](docs/SEARCH.md).

## Translate with explicit online setup

Enable Google Cloud Translation and configure `GOOGLE_TRANSLATE_API_KEY` locally. Then:

```python
english = ket.khtranslate("សួស្តី", target="en")  # Default source: km (Khmer).
khmer = ket.khtranslate("Hello", target="km", source="en")
```

Calling `khtranslate` sends this text to Google and may incur provider charges. It uses the Python standard library, accepts up to 5,000 characters per call, and requires your own credentials. Live translation checks need separate opt-in; protocol tests do not establish translation quality. See [translation setup and validation](docs/TRANSLATION.md).

## Read text from an image or PDF

```python
text = ket.khocr("scan.jpg")
text = ket.khocr("document.pdf")

# Optional: read just the second PDF page.
text = ket.khocr("document.pdf", pages=[2])
```

PDFs are processed one page at a time. Both scanned PDFs and PDFs with embedded text go through OCR. Recognition quality depends on scan quality, font, and the installed Tesseract language data. The existing `khocr` error-string behavior is retained; use `khanalyze` for exception-based error handling.

## Inspect layout when needed

```python
report = ket.khanalyze("document.pdf")  # Also accepts images.
print(report.text)

for page in report.pages:
    print(page.number, page.layout.confidence)
    for line in page.layout.lines:
        print(line.text, line.box)
```

The report contains word boxes, OCR confidence scores, lines, text blocks, geometric column hints, segmented words, and Khmer text diagnostics. It preserves Tesseract's reading order by default. Confidence scores are engine scores, not calibrated probabilities.

Image boxes use top-left-origin pixels after EXIF orientation. PDF boxes use the rendered page's pixels; each page also records its DPI and dimensions in PDF points. Text offsets are local to each page's reconstructed OCR text. Layout analysis covers text regions; it does not classify tables, figures, handwriting, or semantic headings.

See [advanced OCR/layout options](docs/OCR_LAYOUT.md) for column ordering, review overlays, language selection, and coordinate conversion.

## Command line

```bash
# Common daily use:
khmereasytools doctor
khmereasytools process notes.txt
khmereasytools process document.pdf --json
khmereasytools sentences notes.txt
khmereasytools extract notes.txt
khmereasytools ocr scan.jpg
khmereasytools ocr document.pdf

# Ask for details only when you need them:
khmereasytools ocr document.pdf --layout
khmereasytools ocr document.pdf --pages 1,2
khmereasytools ocr scan.jpg --overlay review.png
khmereasytools ocr mixed-text.jpg --lang khm+eng

# Text tools accept UTF-8 files or stdin:
khmereasytools segment document.txt
khmereasytools audit document.txt
khmereasytools normalize document.txt --text-only

# Local retrieval; translation uses your configured Google API key:
khmereasytools search "សៀវភៅ" notes.txt articles.txt
khmereasytools translate document.txt --to en
```

`ocr` and `process` print text by default, with optional JSON reports. `doctor` prints readable setup checks, or JSON with `--json`. Input files are never overwritten. Review overlays currently take image input. Other text commands print JSON except `normalize --text-only`, `digits`, and `translate`.

## Other text tools

- `khfilter(text)` removes built-in stop words; it does not rank keywords.
- `khdigits(text)` translates Khmer digits to ASCII without losing leading zeros; `target="khmer"` reverses it.
- `khaudit(text)` identifies suspicious characters and structural concerns for review.
- `khnormalize(text)` cleans selected formatting and records reversible edits and source mappings.
- `khsyllable(text)` retains the legacy regex heuristic; it is not reliable linguistic syllabification.
- `khpos(text)` is an optional `khmer-nltk` wrapper, installed with `.[khmernltk]`.

See [text quality and mappings](docs/TEXT_QUALITY.md) for cleanup options. To reproduce old `khseg` behavior, use `dictionary="legacy", strategy="legacy"`; to compare greedy matching with the expanded dictionary, use `strategy="longest"`. [Migration notes](docs/EVALUATION.md#migration) describe behavior changes.

## Development and data

```bash
python -m unittest discover -s tests -v
KET_RUN_OCR_TESTS=1 python -m unittest discover -s tests -v
KET_RUN_OCR_TESTS=1 KET_RUN_POS_TESTS=1 python -m unittest discover -s tests -v
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Core tests need only the standard library. Real image/PDF tests additionally need the OCR extra, Tesseract, and `khm` traineddata. Real POS tests use the installed `khmer-nltk` CRF models. CI tests fresh core and `[all]` wheel installations on Windows, macOS, and Linux outside the checkout, with machine-readable reports. The supplied OCR fixture is a clean synthetic rendering; it is not a real-scan accuracy benchmark. See [validation coverage and interpretation](docs/VALIDATION.md).

The expanded dictionary is adapted from ICU under **Unicode License V3**, with a pinned revision, checksums, and reproducible filtering. The original 213-entry lexicon is retained. The external noncommercial khPOS evaluation corpus is not bundled and supplies no runtime vocabulary or frequencies. See [dictionary provenance](docs/DICTIONARY.md), [source history](docs/SOURCE_PROVENANCE.md), and [changelog](CHANGELOG.md).

Project code is MIT licensed; bundled ICU data has its own [Unicode license](khmereasytools/data/UNICODE-LICENSE.txt) and [attribution](khmereasytools/data/DICTIONARY-NOTICE.txt).
