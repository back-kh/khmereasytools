# Lightweight accuracy improvements: protocol, 2026-10-18

Baseline runtime: 43dd811dc969b8357cf8eb1608f8f71379514d36.
Freeze this protocol before evaluating candidate improvements.

## Core segmentation

One candidate: a unigram frequency path decoder using a pinned MIT-licensed
SIL NRSI khmerlbdict frequency source. Retain the existing dictionary and
safe character boundaries, minimize unknown Khmer code points first, then
summed negative log word probability. Missing dictionary frequencies use
add-one smoothing. Custom words get explicit preference. Do not extract any
words, frequencies, or trained weights from evaluation corpora.

Use ALT standard dev IDs for development checks, and reserve its test IDs
and khPOS OPEN-TEST for final before/after comparison. These corpora have
previously been benchmarked; they are reserved from this tuning, not new
historically unseen data. No hyperparameter search on reserved comparisons.

## POS and annotation correction

The installed backend's cache_nova_text implementation combines NOVA
compound components into whole words and uses the outer compound tag.
The previous evaluation used leaves instead. Preserve that historical report;
for this comparison construct whole-word gold using the upstream preparation
semantics and evaluate the unchanged baseline and new runtime identically.
Also retain morpheme-level diagnostics, clearly labeled by granularity.

Candidate: run the existing optional POS CRF directly on chosen words without
space insertion or a second tokenizer. Serialize access to its shared native
tagger. No new model training or downloads. Measure token and joint-tag
span F1 on whole-word ALT gold; keep the four-category khPOS proxy separate.
ALT overlap with upstream model training remains possible.

## OCR

Group all acquisition variants of one document into the same split.
Development IDs: goc_3, mef_1, goc_4, mef_3, goc_2 (20 images).
Reserved IDs: goc_1, mef_2, mef_4, mlvt_1, moh_1, pm_1,
pp_gov_1, pp_gov_2, pp_gov_3, pp_gov_4 (40 images).
goc_3 was visually inspected previously; other dev IDs are selected by
SHA-256 ordering with prefix ket-accuracy-v2:. Prior aggregate baseline
results exist for all pages; this is not a pristine unseen benchmark.

On development images compare the unchanged baseline, enlargement by 2x,
enlargement by 3x, and 2x grayscale/autocontrast. Keep the same fast Khmer
Tesseract model, PSM 3, engine reading order, minimum confidence zero.
Use existing code-point CER normalization/labels. Choose one bounded
small-image preprocessing policy using development CER, then run the
reserved comparison once. No image-specific tuning, spelling correction,
gold crop tuning, or automatic model download.

Preserve source image coordinates: map OCR rectangles back from any enlarged
recognition raster, clamp bounds and recompute derived geometry. Bound total
pixels and subprocess timeout. Plain khocr, structured khanalyze, CLI and
image/PDF processing must share the improved recognition path.

## Validation

Record paired before/after metrics, counts, source/data/model hashes,
dependency versions, model loads, speed and memory tradeoffs. Accuracy is
measured locally on macOS; use fresh native Windows/macOS/Linux wheel installs
for all integration/regression tests, with real OCR/PDF and POS backends.
Keep external corpora/predictions ignored and out of distributions. The core
must retain zero required dependencies. Live translation remains pending.
