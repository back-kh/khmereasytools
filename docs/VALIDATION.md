# Public-function validation

Passing tests establish the documented contracts on checked inputs. They do not establish universal linguistic accuracy. The source version is 0.5.0.dev0; PyPI 0.4.0 does not include the unreleased features.

The [native installation run 39121999874](https://github.com/back-kh/khmereasytools/actions/runs/39121999874)
passed at revision `8b008e507034d513e2148139741a18b39f60827f`, including the
new KhmerRAG, optional local-model translation interface and KET-OCR entry point.
All three operating systems used the same wheel, 526,828 bytes, with SHA-256
`cc05e5b8bf6d8ad9a575b11cca8605ea9d2bdfdad239970eb357430140519ac1`.
The older dataset OCR measurements still use the pinned `b062be0` runtime;
these new interfaces do not change its recognition implementation or results.

| Environment | Windows | macOS | Linux |
| --- | --- | --- | --- |
| Core installation | 161 passed, 19 skipped | 161 passed, 19 skipped | 161 passed, 19 skipped |
| All optional extras | 175 passed, 5 skipped | 175 passed, 5 skipped | 175 passed, 5 skipped |
| Actual OCR and POS | Both executed | Both executed | Both executed |
| Translation quality evaluation | Not performed | Not performed | Not performed |

The suite has 180 tests with no failures in those runs. All-extras skips are
the live Google translation check (disabled by user choice) and four optional
RapidFuzz research-metric tests. Those four metric tests passed in the local
research environment. Model clients use local HTTP fixtures, not live Qwen
generation or a translation-quality evaluation. The [machine-readable
records](../benchmarks/accuracy/daily-tools/native-validation.json) retain the
revision, common wheel hash, dependency versions, and backend flags. These
are installation and contract checks, separate from dataset accuracy.

| Public function | Checks | Interpretation |
| --- | --- | --- |
| `khseg`, `khseg_spans` | Frequency resources/objective, coverage/legacy modes, unknowns, mixed text, offsets, randomized losslessness, exhaustive small decoder checks | khPOS exact-token F1 77.21 -> 78.46%; reserved ALT word F1 66.68 -> 68.29%; corpus limits apply |
| `get_khmer_dictionary` | 81,005-entry count, resource hashes/provenance, independent copies | Bundled lexicon is available and reproducible; membership is not spelling authority |
| `khfilter` | Stop-word removal, empty values, generator vocabulary, legacy options | Removes stop words; does not rank keywords |
| `get_default_stop_words`, `load_stop_words_from_file` | Built-in copies, UTF-8 CSV, duplicates, missing-file legacy contract | Helpers load their documented data |
| `khsyllable` | Regression output and losslessness | Legacy heuristic only; no reliable linguistic syllabification claim |
| `is_khmer` | Khmer presence and Latin-only input | Detects Khmer-block presence, not validity or language identification |
| `khaudit` | Character/letter statistics, suspicious marks, controls, offsets | Diagnostics for review, not a spelling checker |
| `khnormalize` | Conservative defaults, opt-ins, source maps, reversible edits, randomized idempotence | Selected text preparation is traceable |
| `khdigits` | All digits in both directions, leading zeros, mixed scripts | Character translation preserves other text |
| `khocr`, `ket_ocr`, `khocr_layout`, `khanalyze` | Actual image/PDF calls, KET-OCR alias/exception behavior, auto/none parity, source-coordinate rescaling, input cap and paired KHOB images | KET-OCR names the existing Tesseract-based pipeline; reserved image CER 15.99 -> 11.43% locally; historical full-image/PDF baseline retained; output needs review |
| `khlayout`, `khocr_overlay` | TSV validation, block/line/column order, offsets, drawing bounds and source protection | Geometric text-layout helpers, not semantic document classifiers |
| `khpos` | Actual CRF, preserved words/custom terms, no whitespace/second model, concurrent calls and whole-word ALT comparison | Joint word/tag F1 67.40 -> 67.67%; possible training overlap; older leaf-level metrics use different gold |
| `khindex`, `khsearch` | Khmer retrieval, compound recall, BM25 score, digits/case, source offsets, original retrieval and errors | Functional keyword search, not a semantic/large-corpus benchmark |
| `khtranslate`, `LocalModel` | Google and local-model HTTP fixtures, credential/error/timeout handling, no proxy/redirect/cloud fallback, response bounds and truncation errors | Functional client checks; no live translation-quality evaluation |
| `khrag`, `KhmerRAG` | Passage ranking, chunk coverage, exact source offsets, citation mapping, empty/no-match behavior, CLI and local-model HTTP integration | Functional lexical retrieval and optional generation; no judged retrieval or answer-accuracy benchmark |
| `khsentences` | Contracts, 97 reconstructed ALT articles and 40 authored challenges | Internal-boundary F1 99.51% on reconstruction; 37/40 exact challenges after a fix; abbreviation/ellipsis limits remain |
| `khextract` | Contracts plus 50 authored positive/negative cases | 50/50 exact after a phone-boundary fix; adapted development result, not independent precision/recall |
| `khprocess` | UTF-8/BOM/newline mappings, invalid input, unchanged files, real image/PDF processing, original/cleaned coordinate contracts | Local workflow reuses existing core/OCR; OCR quality limits remain unchanged |
| `khdoctor` | Missing packages/engine/language, timeouts, safe key presence, no optional imports, actual installed-environment setup checks | Read-only configuration report, not remote credential or model health verification |

All 26 exported functions have executable tests, along with the new model and RAG classes. See [current paired results](IMPROVEMENTS.md), [historical accuracy limits](ACCURACY.md), [daily tools](DAILY_TOOLS.md), [segmentation protocol](EVALUATION.md), [OCR limits](OCR_LAYOUT.md), [added WER and historical failure audit](OCR_WORD_METRICS.md), [search](SEARCH.md), [KhmerRAG](RAG.md), and [translation](TRANSLATION.md).

## Reproduction

```bash
python -m unittest discover -s tests -v
# Install .[all], Tesseract, and khm traineddata for actual optional backends:
KET_RUN_OCR_TESTS=1 KET_RUN_POS_TESTS=1 python -m unittest discover -s tests -v
```

Optional tests are skipped unless explicitly enabled. Installing optional packages alone does not enable them. Live translation is a separate opt-in described in its guide.

The GitHub Actions workflow builds a wheel and source archive, tests the core on multiple Python versions, and tests fresh wheel installations on Windows, macOS, and Linux with Python 3.11. Each OS runs both a dependency-free core environment and an `[all]` environment outside the source checkout. OCR uses a checksum-pinned official `tessdata_fast` Khmer model; POS uses the actual installed backend, without mocks. Machine-readable artifacts record OS, Python/dependency versions, source revision, wheel checksum, exported functions, executed/skipped tests, failures, backend flags, and setup-check statuses.

These jobs must actually pass before claiming that a particular revision is checked on all three operating systems. Merely having a workflow file is not a passing result. Current Python 3.14/3.15 source tests cover core code; they do not establish optional backend support on those versions. Python 3.6/3.9 checks are legacy core compatibility only, not recommendations to use unsupported runtimes.

The separate [OCR target experiment](OCR_TARGET.md) compares pinned fast and
best Khmer models through the installed image/PDF APIs on all three OSes.
Its accuracy target is reported separately from execution success; a green
workflow does not mean CER is below 10%. Raw full-corpus/development scores
include a documented swapped image/transcript pair; the 40 comparison images
exclude both affected IDs. No new production model or dependency is added.
