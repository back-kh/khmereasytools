# Expanded public OCR comparison 2026 10 18

Protocol established before this experiment's OCR predictions. This is an
evaluation of existing software, not model training or runtime tuning.
Only KHOB and KhmerST are source corpora, as requested by the author.

## Corpora and units

1. KHOB level 1, revision 72b39935f2f12bee5f95d61060a2d1aaa669448b,
   the existing checksum-pinned 2026-01-31 archive. Use the existing 40-image
   comparison partition: ten underlying documents in four acquisition
   variants (digital export, Messenger, physical scanner, scanner application).
   Do not add the five development documents or repair their swapped labels
   for this comparison. This partition is previously examined, not new
   independent evidence. Report acquisition variants separately.
2. KhmerST, original GitLab project 62344518 at revision
   ff64017769af17dee93384756019a975489a7fe0. Fetch all 1,544 original scene
   images and the 31 current JSON annotation files, verifying their Git blob
   identities and recording SHA-256 hashes. Evaluate all usable annotated
   text regions, grouped by source image. This is a fixed public-corpus
   evaluation with no training here; it is not described as the authors'
   official test split or as guaranteed absent from Tesseract training.

KhmerST annotates individual text polygons. Its line_id values can be missing
or repeated, so whole-image concatenation would invent reading-order gold.
The scene experiment is therefore **recognition given gold polygons**, not
end-to-end text detection or whole-scene OCR accuracy. First apply EXIF
orientation to the source pixels. The polygons use upright display
coordinates, as confirmed by pre-prediction visual and coordinate checks.
Crop each polygon's
axis-aligned bounding rectangle, mask pixels outside the polygon white, and
add a two-pixel white border. Do not deskew, rectify, use OCR-dependent crop
selection, or assume perfect annotations. Both systems get the same crop.

Before inference, exclude only missing/blank/non-string transcripts, explicit
### illegibility markers, malformed/non-finite polygons, zero-size crops,
or coordinates outside image bounds by more than one pixel.
Record every exclusion. Clamp at most one-pixel boundary rounding. Fail on
duplicate filenames across annotation files, changed hashes, or absent source
images. Retain all other labels, including numbers, Latin and mixed text.

Preparation correction before any OCR predictions: the initial draft would
exclude non-identity EXIF orientations. A metadata audit found that most
available images use orientation 6, with polygons aligned to the upright
display rather than the sideways raw pixels. Valid orientations 1 through 8
are therefore applied before geometry validation and shared input creation;
unknown orientations and images over 40 million pixels are excluded. This
corrects coordinate handling without consulting OCR outputs or changing any
recognition parameters.

## Matched systems

* Baseline: plain pytesseract.image_to_string with no resizing, contrast
  adjustment, spell correction or language-model postprocessing.
* Toolkit: installed KhmerEasyTools 0.5.0.dev0 khocr_layout, preprocess=auto,
  segment=False, minimum confidence 0, engine reading order.
* Both: the same Tesseract executable, fast khm+eng language order, and pinned
  files below; PSM 3 for full KHOB pages and PSM 7 for scene text crops.
  This explicitly configured mixed-language lane is not the library's
  Khmer-only default. No best-model, per-image choice, or parameter search.
* Both receive the same upright RGB PNG materialization. Record toolkit
  errors and baseline errors, scoring failed outputs as empty text rather
  than dropping difficult examples. Abort only for global setup failures.

Fast model revision: 87416418657359cb625c412a48b6e1d6d41c29bd.
Khmer SHA-256: 47f110575341b322052f3becbefee61a3ecf1ef549352b5d4d33d28afe30d099.
English SHA-256: 7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2.
Runtime Python sources must match the b062be0 development implementation.
Build and install a fresh wheel; execute the harness in Python isolated mode
outside import access to the source package. Pin model checks before calls.

## Controlled synthetic degradation

This is a paired robustness check derived from the same source images, not a
third corpus or additional independent real documents. Apply one fixed
transform: reduce width and height to floor(half), with a minimum of two
pixels, using Lanczos, then encode JPEG quality 40, subsampling 2, and decode
to RGB. For KHOB apply to all 40 full pages. For KhmerST apply to all usable
region crops from the 128 eligible source filenames with the smallest SHA-256 of
the UTF-8 string expanded-ocr-20261018/ plus filename. Choose source IDs
without using their text or predictions. Keep clean and degraded results
separate. Synthetic degradation does not establish real phone-camera quality.

## Scoring and uncertainty

Use existing evaluation_metrics.text_score: NFC, then remove Unicode
whitespace and ZWSP for compact code-point CER. Retain supplementary
whitespace-folded CER. Do not reorder Khmer marks or correct spelling.
Report edits/reference code points, micro CER, median per-unit CER, exact
units, sample counts, failures, and source-group counts. Do not equate cropped
lines, source images, acquisition variants, characters, or OS replications.

Report paired toolkit-minus-baseline CER differences with descriptive 95%
percentile intervals from 5,000 cluster bootstrap replicates, seed 20261018.
Cluster all KHOB variants by document stem; cluster scene regions by source
image SHA-256, merging any byte-identical images. Resample the same groups
for both systems. These intervals assume
independent source groups; duplicate scenes or annotation defects can weaken
that assumption. Do not assert statistical superiority from rounded means.

Set OMP_THREAD_LIMIT=1, use four worker processes, and alternate system call
order deterministically across units. Record wall times as diagnostics under
this concurrent workload, not portable speed claims. No text is uploaded to
an OCR or translation service. Datasets, crops, full gold and predictions stay
under ignored .evaluation. Commit only aggregate/per-unit counts, hashes,
source notices, exclusion reasons without transcript text, and the protocol.

## Scope and availability

KHOB carries an upstream MIT notice. KhmerST is publicly released by its
authors for research; no explicit license was returned by its repository
metadata at inspection, so do not assert a broader redistribution grant.
Do not redistribute the dataset in the package or report. Cite both sources.
No new independent full-page/phone-scan corpus is supplied by this protocol;
that coverage gap remains explicit. No PyPI release, production-default
change, live translation call or SSRN submission is part of this work.
