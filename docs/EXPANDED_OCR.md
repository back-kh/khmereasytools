# Expanded OCR comparison using KHOB and KhmerST

KhmerEasyTools improves aggregate compact code-point CER against the matched plain-Tesseract baseline in all four fixed tracks. Absolute scene and degraded-page errors remain high. The sub-10% overall KHOB target is still unmet; this study supports no general scene-OCR or severe-degradation reliability claim.

## Protocol and source material

The [protocol](../benchmarks/accuracy/EXPANDED_OCR_PROTOCOL.md) and evaluator were frozen at `e569c6a8d73ec06da8c6b55b1ecde073fee5b99a` before OCR predictions. No runtime settings, model files, or thresholds changed during the run. Runtime Python source bytes match `b062be07447f7b9f1bf57f97aab7098d04db165b`. This is unreleased `0.5.0.dev0`, separate from published `0.4.0`.

- **KHOB:** the same 40 previously examined level-1 comparison images from ten government documents, with digital export, Messenger, physical-scanner and scanner-app acquisitions. The five development documents remain excluded. This adds no independently unseen full-page corpus.
- **KhmerST:** all 1,544 original images and 31 annotation files at `ff64017769af17dee93384756019a975489a7fe0` were verified against upstream Git blob IDs. A fixed check excludes `L3I_IMG_1358.jpg`, whose EXIF orientation is 0. The retained 1,543 images provide 3,563 regions and 54,625 reference code points. EXIF rotation is applied before interpreting upright polygon coordinates.
- **Scene grouping:** 1,541 distinct image-SHA-256 clusters. `L3I_IMG_0356.jpg` / `0357.jpg` and `0360.jpg` / `0361.jpg` are byte-identical pairs, retained as released but grouped in uncertainty estimates.
- **Recognition given gold polygons:** white-mask the axis-aligned polygon crop and add a two-pixel border. There is no deskew or perspective rectification. Missing/repeated line IDs do not support whole-scene reading-order gold, so this is not an end-to-end text-detection benchmark.
- **Controlled degradation:** half width and height using Lanczos, JPEG quality 40 with subsampling 2, then decode RGB. This covers all 40 KHOB pages and 320 crops from 128 deterministically selected eligible KhmerST filenames. These dependent variants are not new documents or realistic phone-camera evidence.

## Matched systems and metrics

Local environment: Python 3.9.6, `macOS-26.5.1-arm64-arm-64bit`, Tesseract 5.5.2. Four processes use `OMP_THREAD_LIMIT=1`, and system-call order alternates deterministically. Both systems receive identical upright RGB PNGs and the pinned fast `khm+eng` files. PSM 3 is used for KHOB pages and PSM 7 for scene crops. The mixed-language option is explicitly configured; the library default remains Khmer-only.

The baseline calls `pytesseract.image_to_string` without enhancement. The fresh installed wheel calls `khocr_layout(preprocess="auto", segment=False, min_confidence=0, reading_order="engine")`. This evaluates the packaged pipeline, including TSV-to-text assembly, rather than isolating image preprocessing. The evaluated local wheel is 520,130 bytes with no required core dependencies; external corpora and models are not bundled.

Compact CER applies NFC and removes Unicode whitespace and ZWSP. The denominator is the total reference-code-point count. Failed calls are retained as empty output; none failed in this run. Successful empty strings also remain in every denominator. Supplementary whitespace-folded scores are saved, without treating whitespace units as Khmer linguistic words.

Intervals use 5,000 paired cluster-bootstrap replicates, seed 20261018, resampling the same source groups for both systems. Delta is toolkit minus baseline in CER percentage points, with negative values favoring the toolkit. The intervals are descriptive, assume independent source groups, and have no multiplicity correction. Ten KHOB document groups and possible near-duplicate scenes limit inference.

## Results

| Track | Units / images / groups | Ref code points | Baseline edits / CER | Toolkit edits / CER | Delta points [95% interval] |
| --- | ---: | ---: | ---: | ---: | ---: |
| KHOB original pages | 40 / 40 / 10 | 80,606 | 13,376 / 16.5943% | 8,606 / 10.6766% | -5.9177 [-8.8597, -3.2148] |
| KHOB half resolution JPEG 40 | 40 / 40 / 10 | 80,606 | 65,992 / 81.8698% | 59,537 / 73.8617% | -8.0081 [-12.0272, -4.9720] |
| KhmerST original polygon crops | 3,563 / 1,543 / 1,541 | 54,625 | 36,637 / 67.0700% | 35,912 / 65.7428% | -1.3272 [-2.3413, -0.3449] |
| KhmerST half resolution JPEG 40 | 320 / 128 / 128 | 4,882 | 3,507 / 71.8353% | 3,300 / 67.5952% | -4.2401 [-8.1686, -0.5369] |

The row labels mean original versus synthetically degraded inputs; original KHOB rows already include all four acquisition methods.

| Original KHOB acquisition | Units / images / groups | Ref code points | Baseline edits / CER | Toolkit edits / CER | Delta points [95% interval] |
| --- | ---: | ---: | ---: | ---: | ---: |
| Digital PDF export | 10 / 10 / 10 | 19,694 | 2,482 / 12.6028% | 2,364 / 12.0037% | -0.5992 [-3.4907, +2.1086] |
| Messenger compression | 10 / 10 / 10 | 20,331 | 2,136 / 10.5061% | 1,738 / 8.5485% | -1.9576 [-3.8085, +0.1526] |
| Physical scanner | 10 / 10 / 10 | 20,289 | 3,274 / 16.1368% | 2,038 / 10.0449% | -6.0920 [-7.7981, -4.2151] |
| Scanner application | 10 / 10 / 10 | 20,292 | 5,484 / 27.0254% | 2,466 / 12.1526% | -14.8729 [-22.3881, -8.3358] |

The original KHOB toolkit result reproduces the existing mixed-language score of 8,606 / 80,606 = 10.6766% CER. The baseline in this experiment is plain mixed-language Tesseract, whereas the earlier paired report used an earlier Khmer-only toolkit baseline. The largest acquisition reduction is for scanner-application pages, from 27.03% to 12.15% CER. The digital-export and Messenger intervals include zero; ten source documents support only descriptive uncertainty. The overall sub-10% target remains unmet.

For original KhmerST crops, the toolkit makes 35,912 edits over 54,625 reference code points, or 65.74% CER. Only 277 of 3,563 crops are exact, compared with 269 for the baseline, and median crop CER is 100% for both systems. The toolkit returns 964 empty strings despite zero runtime exceptions. Under page degradation, toolkit CER reaches 73.86%. These results expose substantial recognition failure even with supplied polygons. In the degraded scene subset, aggregate CER improves but exact crops decrease from 26 to 25. Passing backend calls and lower aggregate CER therefore do not establish reliable scene OCR or severe-degradation robustness.

## Diagnostics and validation

| Track | Baseline exact units | Toolkit exact units | Baseline median unit CER | Toolkit median unit CER | Baseline / toolkit exceptions |
| --- | ---: | ---: | ---: | ---: | ---: |
| KHOB original pages | 0 | 0 | 12.88% | 8.60% | 0 / 0 |
| KHOB half resolution JPEG 40 | 0 | 0 | 99.06% | 93.64% | 0 / 0 |
| KhmerST original polygon crops | 269 | 277 | 100.00% | 100.00% | 0 / 0 |
| KhmerST half resolution JPEG 40 | 26 | 25 | 100.00% | 100.00% | 0 / 0 |

An automated consistency audit recomputed all 7,926 prediction scores from local cached text, checked the complete expected unit set, and reproduced the paired aggregates and intervals. It does not independently verify transcripts or constitute human accuracy validation.

[Native installation run 39099422140](https://github.com/back-kh/khmereasytools/actions/runs/39099422140) passes every job at the frozen evaluation revision. Each Windows/macOS/Linux all-extras installation runs 151 tests: 150 pass and live translation is deliberately skipped. Core installations pass 137 tests and skip 14 optional checks. Actual OCR and POS execute. This expanded KhmerST accuracy run is local macOS only; it is not a three-OS scene-accuracy replication. Earlier native KHOB accuracy remains in [OCR_TARGET.md](OCR_TARGET.md).

## Reproduction

Use Python 3.9 or later, Git, a local Tesseract executable, and the evaluation dependencies. Build a wheel, install that exact wheel with OCR extras into a fresh virtual environment, and execute the harness with `python -I`. The runtime source check requires the recorded development implementation.

```bash
python -m pip install build -r requirements-evaluation.txt
python -m build --wheel --outdir .evaluation/expanded_ocr/wheel
python -m pip install --force-reinstall ".evaluation/expanded_ocr/wheel/khmereasytools-0.5.0.dev0-py3-none-any.whl[ocr]"
python scripts/fetch_accuracy_data.py
python scripts/fetch_expanded_ocr.py --images --workers 4
python -I scripts/evaluate_expanded_ocr.py --prepare-only
python -I scripts/evaluate_expanded_ocr.py --wheel .evaluation/expanded_ocr/wheel/khmereasytools-0.5.0.dev0-py3-none-any.whl
```

The existing `fetch_accuracy_data.py` fetches the KHOB archive and the text resources used in the earlier NLP study; only KHOB and KhmerST enter this OCR comparison. Original KhmerST data total approximately 3.9 GiB and stay under ignored `.evaluation`. The default KhmerST downloader now uses a partial Git clone with bulk sparse checkout and verifies every blob; optional `--transport api` respects server cooldowns.

For exact image-processing reproduction, use the Python, Pillow, pytesseract, rapidfuzz and Tesseract versions recorded in `local-paired.json`. The downloader disables Git line-ending conversion so original annotation bytes survive Windows checkouts.

Before running inference, place these two original fast model files in `.evaluation/ocr-target/tessdata-mixed/` (or pass `--tessdata-dir`). The evaluator checks their pinned SHA-256 values:

- [khm.traineddata](https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/87416418657359cb625c412a48b6e1d6d41c29bd/khm.traineddata): `47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099`.
- [eng.traineddata](https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/87416418657359cb625c412a48b6e1d6d41c29bd/eng.traineddata): `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.

Cached predictions are resumed only for identical recorded settings and fingerprints. Times describe a concurrent local workload and support no portable speed claim. No OCR text is uploaded to a provider; no live translation calls were made.

## Artifacts and sources

- [Paired measurements and per-unit counts](../benchmarks/accuracy/expanded-ocr/local-paired.json).
- [Complete pinned source inventory](../benchmarks/accuracy/expanded-ocr/source-inventory.json).
- [Automated consistency audit](../benchmarks/accuracy/expanded-ocr/consistency-audit.json).
- [Native installed-wheel validation records](../benchmarks/accuracy/expanded-ocr/native-validation.json).
- [KHOB original repository](https://github.com/EKYCSolutions/khmer-ocr-benchmark-dataset), revision `72b39935f2f12bee5f95d61060a2d1aaa669448b`, upstream MIT notice. The 40-page partition still has unreviewed transcript/ordering limits.
- [KhmerST paper](https://arxiv.org/abs/2410.18277) and [original dataset revision](https://gitlab.com/vannkinhnom123/khmerst/-/tree/ff64017769af17dee93384756019a975489a7fe0). Its published train/test split and recognition configuration differ from this full-corpus, current-annotation comparison. No explicit dataset license was recovered from the original repository metadata at inspection; images and transcripts are not redistributed.
- [Official Tesseract command documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html) and [manual](https://github.com/tesseract-ocr/tesseract/blob/main/doc/tesseract.1.asc).
- [Dror et al. 2018](https://aclanthology.org/P18-1128/) discusses statistical comparisons and limitations from small or dependent NLP samples.

No independent new full-page/phone-scan corpus, perspective correction, modern scene recognizer, model training, new runtime dependency, release, or production-default change is introduced by this evaluation.
