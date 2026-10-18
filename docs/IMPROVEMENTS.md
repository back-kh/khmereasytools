# Lightweight accuracy improvements

The current 0.5 development source improves segmentation, POS and small-image
OCR while keeping core runtime dependencies empty. Daily calls remain:

~~~python
import khmereasytools as ket
words = ket.khseg("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ")
tags = ket.khpos("ខ្ញុំស្រឡាញ់ភាសាខ្មែរ")  # Optional POS installation.
text = ket.khocr("scan.jpg")               # Optional OCR setup; PDF also works.
~~~

No service, new model download, or configuration choice is needed for these
improvements. The optional packages/system engine are still installed once.
PyPI 0.4.0 remains the published version until a separate release.

## Paired results

Local macOS arm64, Python 3.9.6; same datasets/dependencies/model files before
and after. The baseline is commit 43dd811dc969b8357cf8eb1608f8f71379514d36.
The reserved partition was excluded from this tuning, but prior benchmark
results existed. Do not describe it as a new historically unseen test set.

| Check | Before | After | Sample |
| --- | ---: | ---: | --- |
| khPOS exact-token F1 | 77.21% | 78.46% | 1,000 sentences / 10,778 tokens |
| ALT whole-word segmentation F1 | 66.68% | 68.29% | 1,018 sentences / 26,551 word tokens |
| ALT joint word/POS span F1 | 67.40% | 67.67% | Same whole-word gold |
| Default OCR code-point CER, lower is better | 15.99% | 11.43% | 40 images: 10 underlying documents, four variants each |

The POS improvement is small, about 0.27 percentage points. Segmentation is
still a substantial source of errors. No statistical significance or general
accuracy claim follows from these samples. ALT may overlap the backend's
training data, and KHOB annotations have known alignment/reading-order limits.
No independently human-reviewed new daily-document corpus is claimed.

The full development reports, selection decision, and paired reserved reports
are in [accuracy artifacts](../benchmarks/accuracy/README.md). Gold text/images
and full external predictions are not distributed. The same paired comparisons
also run in the native Windows/macOS/Linux accuracy workflow; its uploaded
reports identify the OS, engine/model/source hashes and tested wheel.

## Changes and costs

### Segmentation

The decoder minimizes unknown Khmer code points first, then the sum of
smoothed unigram word costs. It can prefer common words to an unlikely long
dictionary combination. Unknown text and all source offsets remain lossless.
Custom words are local exact candidates with explicit preference.

The 16,546-entry frequency table is the existing dictionary's intersection with
[SIL NRSI khmerlbdict](https://github.com/silnrsi/khmerlbdict/tree/54abc6b87f4ffa6a0c95c09836c7c86648002273),
under its upstream MIT notice with attribution to the original SEALang list.
The 81,005-entry vocabulary is unchanged. No evaluation-corpus words, counts,
correction rules or trained weights enter the runtime data.
Pinned hashes, SIL license and a notice ship with the package.
The wheel grows from about 413 KiB to about 507 KiB; core dependencies stay empty.

~~~bash
python scripts/build_frequencies.py
~~~

Frequency costs are ranking preferences, not spelling authority or calibrated
confidence. Domains and compound conventions can still disagree with them.
For earlier 0.5 behavior, use khseg(text, strategy="coverage") and the same
option on khseg_spans/khfilter; longest remains available. For 0.4 behavior,
specify dictionary="legacy", strategy="legacy" on khseg/khfilter.

### POS

khpos applies the actual optional backend CRF to the chosen words. It does
not insert spaces, return whitespace as noun tokens, or invoke a second
word tokenizer. Custom vocabulary is accepted through custom_words.
Shared native model access is serialized for concurrent khpos calls.

The existing khmer-nltk dependency still contains both upstream model files
on disk, but this adapter loads only the 2.8 MB POS model and avoids loading
the 17.7 MB tokenizer model. In fresh local benchmark processes, peak RSS for
text checks decreased from 163.2 to 142.2 MiB. These are whole-process peaks,
not isolated model sizes or guarantees across Python/dependency versions.
The ALT text check took 3.02 -> 1.93 seconds; this is a single-run diagnostic,
not a general speed benchmark.

### OCR

Auto preprocessing is now shared by khocr, khocr_layout, khanalyze, khprocess
and the CLI. If the longest edge is below 1600 pixels, Pillow applies grayscale,
autocontrast and 2x Lanczos enlargement before one Tesseract call. Larger
images retain the previous pixel path. The fast Khmer model is unchanged.
No OCR spelling correction or image-specific tuning is applied.

Rectangles are mapped outward and clamped to original upright image pixels;
overlays and PDF point conversion retain their source coordinate system.
Input images are unchanged. A 40-million-pixel input cap is checked before
conversion, and the existing subprocess timeout remains bounded.

~~~python
text = ket.khocr("scan.jpg", preprocess="none")  # Earlier pixel processing.
layout = ket.khanalyze("scan.jpg", preprocess="none")
~~~

Explicit grayscale and threshold modes retain their previous meaning without
enlargement. The structured result records when auto enlargement was used.
Plain image OCR now shares structured text reconstruction, so whitespace
formatting may differ from the earlier image_to_string path.

The 40-image check took 34.4 -> 43.0 seconds locally: the accuracy gain costs
additional OCR time and temporary image memory. Large images, scene text,
handwriting, semantic layout and tables are not newly validated by this policy.

## Corrected POS evaluation granularity

The [historical accuracy report](ACCURACY.md) used NOVA leaf tags and scored
36,007 component tokens. Upstream khmer-nltk cache_nova_text combines
compound components and assigns the outer compound tag. This comparison
therefore scores 26,551 whole-word tokens, applying exactly the same adapter
to baseline and improved code. The gold parser has independent unit tests.
The annotation correction itself is not counted as a runtime improvement.
The old leaf-level measurements remain available rather than being overwritten.

## Reproduce

~~~bash
python -m pip install '.[all]' -r requirements-evaluation.txt
python scripts/fetch_accuracy_data.py
python scripts/compare_improvements.py --name current_reserved --partition reserved
# Against a fresh installed wheel, outside the source tree:
python scripts/run_accuracy_ci.py --dist dist
~~~

See the frozen [protocol](../benchmarks/accuracy/IMPROVEMENT_PROTOCOL.md)
and [development selection](../benchmarks/accuracy/IMPROVEMENT_SELECTION.md).
The accuracy workflow runs for relevant benchmark/algorithm changes and can
also be manually dispatched once present on the default branch. It installs
the wheel in a fresh environment and compares with the pinned baseline.
Reports contain derived counts, not external gold text. Translation remains
pending by user choice, with no live provider requests in these checks.
