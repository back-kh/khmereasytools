# Public-function validation

Passing tests establish the documented contracts on checked inputs. They do not establish universal linguistic accuracy. The source version is 0.5.0.dev0; PyPI 0.4.0 does not include the unreleased features.

| Public function | Checks | Interpretation |
| --- | --- | --- |
| `khseg`, `khseg_spans` | Known words, expanded/legacy modes, unknowns, mixed text, code-point offsets, randomized losslessness, exhaustive small decoder comparison | Functional coverage; independent khPOS OPEN-TEST exact-token F1 is 77.21 on one corpus |
| `get_khmer_dictionary` | 81,005-entry count, resource hashes/provenance, independent copies | Bundled lexicon is available and reproducible; membership is not spelling authority |
| `khfilter` | Stop-word removal, empty values, generator vocabulary, legacy options | Removes stop words; does not rank keywords |
| `get_default_stop_words`, `load_stop_words_from_file` | Built-in copies, UTF-8 CSV, duplicates, missing-file legacy contract | Helpers load their documented data |
| `khsyllable` | Regression output and losslessness | Legacy heuristic only; no reliable linguistic syllabification claim |
| `is_khmer` | Khmer presence and Latin-only input | Detects Khmer-block presence, not validity or language identification |
| `khaudit` | Character/letter statistics, suspicious marks, controls, offsets | Diagnostics for review, not a spelling checker |
| `khnormalize` | Conservative defaults, opt-ins, source maps, reversible edits, randomized idempotence | Selected text preparation is traceable |
| `khdigits` | All digits in both directions, leading zeros, mixed scripts | Character translation preserves other text |
| `khocr`, `khocr_layout`, `khanalyze` | Real image/PDF Tesseract calls, Khmer model, blank pages, page selection and geometry | Engine integration on synthetic fixtures; real-scan OCR accuracy remains unmeasured |
| `khlayout`, `khocr_overlay` | TSV validation, block/line/column order, offsets, drawing bounds and source protection | Geometric text-layout helpers, not semantic document classifiers |
| `khpos` | Real installed khmer-nltk models, known verb/noun output, punctuation and empty text | Real backend execution; not an independent POS accuracy evaluation |
| `khindex`, `khsearch` | Khmer retrieval, compound recall, BM25 score, digits/case, source offsets, original retrieval and errors | Functional keyword search, not a semantic/large-corpus benchmark |
| `khtranslate` | Local HTTP protocol, credential/error/timeout handling; separately gated live checks | Live provider checks pending by user choice; translation quality unmeasured |

All 20 exported functions have executable tests. See [segmentation protocol](EVALUATION.md), [OCR limits](OCR_LAYOUT.md), [search](SEARCH.md), and [translation](TRANSLATION.md) for the limits of each result.

## Reproduction

```bash
python -m unittest discover -s tests -v
# Install .[all], Tesseract, and khm traineddata for actual optional backends:
KET_RUN_OCR_TESTS=1 KET_RUN_POS_TESTS=1 python -m unittest discover -s tests -v
```

Optional tests are skipped unless explicitly enabled. Installing optional packages alone does not enable them. Live translation is a separate opt-in described in its guide.

The GitHub Actions workflow builds a wheel and source archive, tests the core on multiple Python versions, and tests fresh wheel installations on Windows, macOS, and Linux with Python 3.11. Each OS runs both a dependency-free core environment and an `[all]` environment outside the source checkout. OCR uses a checksum-pinned official `tessdata_fast` Khmer model; POS uses the actual installed backend, without mocks. Machine-readable artifacts record OS, Python/dependency versions, exported functions, executed/skipped tests, failures, and backend flags.

These jobs must actually pass before claiming that a particular revision is checked on all three operating systems. Merely having a workflow file is not a passing result. Current Python 3.14/3.15 source tests cover core code; they do not establish optional backend support on those versions. Python 3.6/3.9 checks are legacy core compatibility only, not recommendations to use unsupported runtimes.
