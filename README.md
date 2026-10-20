# Khmer Easy Tools

Everyday Khmer tools: split words, inspect Khmer grammar with KET-Tagger, search local text, retrieve passages with KhmerRAG, read images or PDFs with KET-OCR, and inspect document layouts. Core text, tagging, search and retrieval run offline with **no runtime dependencies or model downloads**. Translation and RAG answer generation use an explicitly configured provider or local model.

The new **0.5.0.dev0** source version adds an **81,005-entry dictionary**, better segmentation, sentence splitting, structured extraction, one-call file processing, local search, optional translation, and setup diagnostics. PyPI 0.4.0 remains the published version until this update is released.

[Paired accuracy evaluation](docs/IMPROVEMENTS.md) now compares the earlier
and improved defaults. Segmentation F1 rises from 77.21% to 78.46% on khPOS;
whole-word POS joint F1 rises modestly from 67.40% to 67.67% on ALT; OCR
character error rate falls from 15.99% to 11.43% on 40 reserved page images.
These samples have documented overlap/annotation limits. Review output where
errors matter. Core tools remain dependency-free; the wheel remains under 1 MiB.

The [sub-10% OCR experiment](docs/OCR_TARGET.md) did not meet that target:
the optional larger model scored 11.49% versus 11.43% for the default on the
same 40 images. The default is unchanged. A swapped transcript/image pair
was also found in development data; historical raw reports remain preserved.
An additional adaptive `khm+eng` check improves this local image score to
10.68%, still above target; use that existing explicit mode for mixed text.

Recorded research comparisons cover a [150-page historical OCR study](docs/DOCUMENT_OCR.md)
and an [exploratory small Qwen comparison](docs/SMALL_VLM.md). Their external
frameworks and model weights are not toolkit requirements. A separate KH-FUNSD
comparison uses author-designated, machine-generated references with their
unreviewed status disclosed; they are not certified human transcripts.
The completed [146-image KH-FUNSD comparison](docs/KHFUNSD_OCR.md) and
[added WER and historical failure audit](docs/OCR_WORD_METRICS.md) retain all
empty, failed and capped outputs. See [native function validation](docs/VALIDATION.md)
for fresh Windows, macOS and Linux installation results.

A [smaller printed-document diagnostic](docs/CLEAN_DOCUMENT_DIAGNOSTIC.md)
retains 18 input-screened images in separate KHOB and KH-FUNSD tracks. It is a
post hoc development sample with disclosed selection and reference limits;
the larger comparisons remain unchanged.

## Install

Software code is MIT licensed. The bundled trained KET-Tagger model and its
derived vocabulary/counts use **CC BY-NC-SA 4.0** for research/noncommercial
use; see the [model license](khmereasytools/data/research/LICENSE.txt).
The independently authored helper remains available with `model="rules"`.

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

The default considers complete paths, minimizing unknown Khmer characters and then summed unigram costs from 16,546 pinned frequency entries. This helps resolve ambiguous dictionary combinations. It does not guess missing OCR characters or change spellings. Dictionary entries include compounds and phrases, so output can still differ from your preferred boundaries. Use `strategy="coverage"` for the earlier token-count objective.

On the 1,000-sentence khPOS OPEN-TEST, exact-token F1 is **78.46%**, compared with **77.21%** for the earlier coverage decoder, **10.8%** for old `khseg` and **30.4%** for the old lossless span tokenizer. These are single-corpus results, not universal accuracy. See [paired results](docs/IMPROVEMENTS.md) and [historical protocol](docs/EVALUATION.md).

For annotations, `khseg_spans(text)` preserves every input character, including spaces and punctuation, and gives `text`, `start`, `end`, and `kind` for each token. Offsets are Python code points with exclusive ends. Custom vocabulary is local to the call.

`khpos(text)` applies the optional POS CRF directly to the chosen words,
preserving boundaries without whitespace tokens or a second tokenizer model.
Use `khpos(text, custom_words=["your domain term"])` for local vocabulary.

## Tag Khmer grammar offline

```python
assert ket.khtag("ខ្ញុំអានសៀវភៅ។") == [
    ("ខ្ញុំ", "PRON"), ("អាន", "VERB"),
    ("សៀវភៅ", "NOUN"), ("។", "PUNCT")]

tokens = ket.khtag("សិស្ស៣នាក់កំពុងអាន។", with_spans=True)
print([(t.text, t.label_km, t.role) for t in tokens])
# Local name/domain overrides:
tagger = ket.KhmerTagger({"និមល": "PROPN"})
```

**KET-Tagger** uses a 239 KiB supervised research model trained on real khPOS
annotations. Its decoder uses only Python's standard library. It includes Khmer
POS names, heuristic particle/aspect/classifier roles, source spans, lexical
alternatives, explanations and local vocabulary. No model download is needed.
The shared 81,005-entry dictionary and `khseg` behavior are unchanged.

After removing exact train/test overlaps, reserved khPOS native POS accuracy is
**95.94% at gold word boundaries**; joint word/POS F1 from unsegmented text is
**87.78%**. On the same ALT coarse diagnostic used before, accuracy rises from
37.61% to **81.07%**, with every word receiving a prediction. Prediction rate
is not correctness; fine particle roles still have no independent gold. Use
`model="rules"` for the earlier authored helper. See [data, licensing and full
evaluation limits](docs/TAGGER.md).

```bash
khmereasytools tag notes.txt
khmereasytools ket-tagger notes.txt --term និមល=PROPN
```

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

## Simple KhmerRAG

```python
rag = ket.KhmerRAG(documents)
result = rag.ask("សៀវភៅ")
print(result.context)  # Retrieved passages with [1], [2], ... and source offsets.

# Optional generation, after installing a local server and model separately:
# model = ket.LocalModel("qwen2.5:3b")
# rag = ket.KhmerRAG(documents, generator=model)
# print(rag.ask("សៀវភៅ").answer)
```

No model is needed to retrieve passages. With a configured generator, the prompt
asks for evidence-based answers and citations; generated answers remain
unverified. See [KhmerRAG setup and limits](docs/RAG.md).

## Translate with explicit setup

Enable Google Cloud Translation and configure `GOOGLE_TRANSLATE_API_KEY` locally. Then:

```python
english = ket.khtranslate("សួស្តី", target="en")  # Default source: km (Khmer).
khmer = ket.khtranslate("Hello", target="km", source="en")
```

Calling `khtranslate` sends this text to Google and may incur provider charges. It uses the Python standard library, accepts up to 5,000 characters per call, and requires your own credentials. Live translation checks need separate opt-in; protocol tests do not establish translation quality. See [translation setup and validation](docs/TRANSLATION.md).

For a separately installed local Qwen model, pass
`local_model=ket.LocalModel("your-installed-model")` to `khtranslate`.
Configure the server for local-only inference as described in the translation
guide. The package does not download weights or run a translation benchmark.

KET-OCR names the Khmer Easy Tools preparation/layout pipeline using Tesseract:
`ket.ket_ocr("document.pdf", lang="khm+eng")` returns text and raises errors on
failure. `khmereasytools ket-ocr document.pdf` is an alias for the existing OCR
CLI. This name does not denote a newly trained recognition model.

## Read text from an image or PDF

```python
text = ket.khocr("scan.jpg")
text = ket.khocr("document.pdf")

# Optional: read just the second PDF page.
text = ket.khocr("document.pdf", pages=[2])
```

PDFs are processed one page at a time. Small images use bounded grayscale/2x enlargement automatically; original image coordinates are preserved. Use `preprocess="none"` to retain earlier pixel processing. Both scanned PDFs and PDFs with embedded text go through OCR. Quality still depends on scan quality, font and installed language data. `khocr` retains error strings; use `khanalyze` for exception-based handling.

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
