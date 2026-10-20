# Khmer Easy Tools

![Khmer Easy Tools: everyday Khmer text and document tools, with 81,005 dictionary entries, a 239 KiB POS model and no core runtime dependencies](https://raw.githubusercontent.com/back-kh/khmereasytools/main/docs/assets/overview.png)

[![Tests](https://github.com/back-kh/khmereasytools/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/back-kh/khmereasytools/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/khmereasytools.svg)](https://pypi.org/project/khmereasytools/)
[![Code: MIT](https://img.shields.io/badge/code-MIT-007D73)](LICENSE)

Everyday Khmer text and document tools: clean text with an edit record, split
words, inspect POS tags, extract useful patterns, search local files, retrieve
passages, and read images or PDFs. Core text, KET-Tagger and retrieval work
offline with **no runtime dependencies or model downloads**.

**Version:** this README describes the **0.5.0.dev0 GitHub source**. The current
[PyPI release is 0.4.0](https://pypi.org/project/khmereasytools/); install from
source for the features shown here. Software is MIT; the bundled trained POS
model and its derived vocabulary/counts are **CC BY-NC-SA 4.0**, for research
and noncommercial use. [License details](MODEL_LICENSES.md).

[Quick start](#quick-start) · [Features](#what-you-can-do) ·
[Architecture](#how-it-fits-together) · [Evidence](#measured-results) ·
[Poster](#poster-and-editable-figures) · [API guide](docs/FEATURES.md)

## Quick start

Install the current GitHub source:

```bash
git clone https://github.com/back-kh/khmereasytools.git
cd khmereasytools
python -m pip install .
khmereasytools doctor
```

```python
import khmereasytools as ket

assert ket.khseg("បច្ចេកវិទ្យាព័ត៌មាន") == ["បច្ចេកវិទ្យា", "ព័ត៌មាន"]
assert ket.khtag("ខ្ញុំអានសៀវភៅ។") == [
    ("ខ្ញុំ", "PRON"), ("អាន", "VERB"),
    ("សៀវភៅ", "NOUN"), ("។", "PUNCT"),
]
assert ket.khdigits("០០៧ / ១២.៥%") == "007 / 12.5%"
```

Use a maintained Python version. Core code retains Python 3.6 compatibility;
optional packages have their own Python requirements. To install the older
published release instead, use `python -m pip install khmereasytools`.

## What you can do

| Task | Main interface | Setup |
| --- | --- | --- |
| Audit and clean text, preserving an edit record | `khaudit`, `khnormalize`, `khdigits`, `khfilter` | Core |
| Split words and keep original positions | `khseg`, `khseg_spans`, `get_khmer_dictionary` | Core; 81,005 dictionary entries |
| Tag Khmer word classes and inspect grammar hints | `khtag`, `KhmerTagger` | Core; 239 KiB bundled research model |
| Split sentences and extract contacts, dates and numbers | `khsentences`, `khextract` | Core; documented heuristics |
| Process a text file in one call | `khprocess` | Core; OCR setup for images/PDFs |
| Search and retrieve local passages | `khindex`, `khsearch`, `KhmerRAG`, `khrag` | Core; BM25, no embedding model |
| Read images/PDFs and inspect text geometry | `ket_ocr`, `khocr`, `khanalyze`, `khocr_layout` | Optional OCR packages + Tesseract |
| Translate or generate an answer | `khtranslate`, `LocalModel`, a RAG generator | Explicit provider/local server setup |
| Check installed capabilities | `khdoctor` or `khmereasytools doctor` | Core; read-only checks |

There are **27 public functions**, plus result/index/model classes. The
[complete API guide](docs/FEATURES.md) also covers layout overlays, the optional
legacy `khpos` backend, stop-word helpers and compatibility functions.

## How it fits together

![Architecture: local text preparation, segmentation, tagging and retrieval; optional Tesseract OCR feeds text into the core; translation and generated answers require explicit provider setup](https://raw.githubusercontent.com/back-kh/khmereasytools/main/docs/assets/architecture.png)

KET-OCR is the toolkit's preparation and layout pipeline **using Tesseract**.
It is not a newly trained recognizer. Translation and answer generation are
optional clients; models and services are configured separately. Importing
the package does not start a server, fetch weights or contact a provider.

## Examples for daily use

### Clean text with a source map

```python
raw = "\ufeffកាា\u200b ១២\r\nខ្មែរ"
audit = ket.khaudit(raw)
cleaned = ket.khnormalize(
    raw, zero_width_space="space", digits="ascii", collapse_spaces=True,
)
assert cleaned.text == "កាា 12\nខ្មែរ"
assert cleaned.original == raw
assert cleaned.source_spans[0] == (1, 2)
```

The repeated vowel is flagged for review and remains in the text. Cleanup
does not guess spellings or reorder Khmer characters. Token offsets use Python
code points with exclusive ends: `text[start:end]`.
[Text quality and reversible edits](docs/TEXT_QUALITY.md).

### Inspect tags and customize names

![Actual KET-Tagger output: Khmer source text split into PRON, VERB, NOUN and PUNCT, with original source offsets](https://raw.githubusercontent.com/back-kh/khmereasytools/main/docs/assets/tagging-workflow.png)

```python
tokens = ket.khtag("សិស្ស៣នាក់កំពុងអាន។", with_spans=True)
print([(t.text, t.label_km, t.role) for t in tokens])

tagger = ket.KhmerTagger({"និមល": "PROPN"})
assert tagger.tag("និមលអាន។")[0] == ("និមល", "PROPN")
```

Custom vocabulary is local to the call or tagger. Learned POS predictions and
heuristic aspect/particle roles are identified in explanations; no calibrated
confidence is claimed. `model="rules"` selects the authored helper without
loading the corpus-derived weights. The shared `khseg` dictionary is unchanged
by the model's private segmentation vocabulary. [KET-Tagger guide](docs/TAGGER.md).

### Search and retrieve passages locally

```python
documents = {
    "school": "សិស្សអានសៀវភៅនៅសាលារៀន។",
    "food": "ខ្ញុំញ៉ាំបាយ។",
}
index = ket.khindex(documents)
assert index.search("សៀវភៅ")[0].document_id == "school"

rag = ket.KhmerRAG(documents)
result = rag.ask("សៀវភៅ")
print(result.context)  # Passages with source references; no model needed.
```

Retrieval uses lexical BM25 with Khmer compound recall and original-source
offsets. A separately configured generator can produce answers; those answers
remain unverified. [Search](docs/SEARCH.md) · [KhmerRAG](docs/RAG.md).

### Process text, images and PDFs

```python
report = ket.khprocess("notes.txt")
print(report.text, report.sentences, report.entities)

# After optional OCR setup:
# text = ket.ket_ocr("document.pdf", lang="khm+eng")
# document = ket.khanalyze("scan.jpg")
```

Add OCR once with `python -m pip install '.[ocr]'`, then install
[Tesseract and Khmer language data](https://tesseract-ocr.github.io/tessdoc/Installation.html).
On Debian/Ubuntu: `sudo apt-get install tesseract-ocr tesseract-ocr-khm`.

PDFs are rendered one page at a time. Results can include words, lines, blocks,
column hints and original-image boxes. These are geometric text-layout helpers;
they do not classify tables, figures or semantic headings. `ket_ocr` raises
exceptions on failure; `khocr` retains its legacy error-string contract.
[Image/PDF setup and layouts](docs/OCR_LAYOUT.md) · [Daily tools](docs/DAILY_TOOLS.md).

Translation uses an explicitly configured Google Cloud Translation account or
local model server. Google calls send text to that service and may incur
charges. **Live translation quality has not been evaluated.**
[Setup, limits and local Qwen usage](docs/TRANSLATION.md).

### Command line

```bash
khmereasytools doctor
khmereasytools process notes.txt
khmereasytools tag notes.txt
khmereasytools extract notes.txt
khmereasytools search "សៀវភៅ" notes.txt articles.txt
khmereasytools ocr document.pdf --pages 1,2 --lang khm+eng
khmereasytools ocr scan.jpg --overlay review.png
```

Inputs are not overwritten. Text commands accept UTF-8 files or stdin; use
`--help` for JSON, source-span and language options.

## Measured results

![Three separate fixed comparisons: segmentation F1 77.21 to 78.46 on khPOS OPEN; ALT coarse POS accuracy 37.61 to 81.07 at gold boundaries; KHOB code-point CER 15.99 to 11.43 on 40 images](https://raw.githubusercontent.com/back-kh/khmereasytools/main/docs/assets/evaluation.png)

The chart compares the same inputs within each panel. It does not compare
different tasks against each other or establish statistical significance.

| Current result | Evaluation scope |
| --- | --- |
| `khseg`: **78.46% exact-token F1** | khPOS OPEN, 1,000 sentences / 10,778 tokens; previously observed diagnostic |
| Native KET-Tagger: **95.94% POS accuracy**, **87.78% joint word/POS F1** | Purged khPOS CLOSE, 1,000 sentences / 10,397 tokens; accuracy uses gold word boundaries, joint F1 uses unsegmented reconstruction |
| Public mapped tags: **94.23% accuracy**, **86.04% joint F1** | Same CLOSE examples; practical public-label projection, not validated UD annotation |
| KET-Tagger: **81.07% coarse POS accuracy** | ALT, 1,018 sentences / 26,551 words; gold boundaries and lossy seven-class mapping |
| Default OCR: **11.43% code-point CER** | 40 KHOB images, representing 10 documents with four variants each; local paired comparison |

All CLOSE sentences appeared in the original khPOS training file. We removed
exact normalized CLOSE/OPEN/ALT matches before training the compact model:
9,827 training and 1,098 development sentences remain. Related articles or
templates may still cross splits. Fine grammar roles lack independent gold.
[Protocol, audit and complete tagger results](docs/TAGGER.md).

OCR is sensitive to fonts, image quality, reading order and reference quality;
general **CER below 10% is not established**. Full scene-text, historical and
KH-FUNSD comparisons remain separate, with failures retained. KH-FUNSD uses
unreviewed machine-generated operational references, so its numbers describe
agreement rather than certified human-gold accuracy. Sentence/extraction
results include authored or reconstructed examples.
[Paired improvements](docs/IMPROVEMENTS.md) ·
[OCR target](docs/OCR_TARGET.md) · [Research records](benchmarks/accuracy/README.md).

## Windows, macOS and Linux validation

| Fresh installed-wheel check | Windows | macOS | Linux |
| --- | --- | --- | --- |
| Core suite | 203 passed / 19 skipped | 203 passed / 19 skipped | 203 passed / 19 skipped |
| All-extras suite | 217 passed / 5 skipped | 217 passed / 5 skipped | 217 passed / 5 skipped |
| Actual Khmer image/PDF OCR + optional native POS | Executed | Executed | Executed |
| Full compact POS corpus replay | 2,000 sentences, exact count match | 2,000 sentences, exact count match | 2,000 sentences, exact count match |

These recorded checks passed on the code before this README refresh
([source `82f96d8`](https://github.com/back-kh/khmereasytools/actions/runs/39383304423)).
The suite discovers 222 tests; extras skips are four optional research-metric
checks and live Google translation. Passing installation tests is distinct
from linguistic accuracy. [Validation coverage and historical records](docs/VALIDATION.md).

## Poster and editable figures

<a href="docs/assets/poster.pdf"><img src="https://raw.githubusercontent.com/back-kh/khmereasytools/main/docs/assets/poster.png" width="520" alt="A3 technical poster covering features, architecture, evaluation scopes, installation checks and licensing"></a>

[Download the A3 poster PDF](docs/assets/poster.pdf) ·
[Architecture SVG](docs/assets/architecture.svg) ·
[Tagging example SVG](docs/assets/tagging-workflow.svg) ·
[Comparison SVG](docs/assets/evaluation.svg).

All figures are generated from existing checked-in evidence and documented
examples. The [asset guide and manifest](docs/assets/README.md) identify source
hashes, exact values and regeneration instructions. No additional dataset or
new training experiment was introduced for this update.

## Development, data and licensing

```bash
python -m unittest discover -s tests -v
python scripts/check_tagger_source.py
python -m pip install build twine
python -m build
python -m twine check dist/*
```

For real optional-backend tests, install `.[all]`, Tesseract and `khm` data,
then set `KET_RUN_OCR_TESTS=1` and `KET_RUN_POS_TESTS=1`. Evaluation downloads
and live translation are explicit, separate actions. The poster/figure
authoring packages are not runtime dependencies.

- **Software and authored rules:** [MIT](LICENSE).
- **Trained POS weights, learned vocabulary and counts:**
  [CC BY-NC-SA 4.0](khmereasytools/data/research/LICENSE.txt), derived from khPOS
  by Vichet Chea and Ye Kyaw Thu. [Model licensing](MODEL_LICENSES.md).
- **Shared 81,005-entry dictionary:** ICU adaptation under
  [Unicode License V3](khmereasytools/data/UNICODE-LICENSE.txt), retaining the
  original 213-entry lexicon. [Dictionary provenance](docs/DICTIONARY.md).
- **Shared segmentation frequencies:** 16,546 pinned SIL NRSI entries with
  [their MIT attribution notice](khmereasytools/data/FREQUENCY-NOTICE.txt).

The trained tagger's private model vocabulary is separate from the shared
segmentation dictionary/frequencies. External raw evaluation corpora and full
predictions are not bundled. [Source history](docs/SOURCE_PROVENANCE.md) ·
[Changelog](CHANGELOG.md) · [Complete API](docs/FEATURES.md).

Maintained by **Nimol Thuon**.
