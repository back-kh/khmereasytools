# Focused printed-document diagnostic

This is a small, post hoc diagnostic for clear, modern printed documents. It
is prepared after the larger studies and after their aggregate results were
known. It is not a new unseen test set, a replacement for those studies, or a
claim of independently verified transcription accuracy.

## Selection before subset scoring

Selection reads source images, source metadata and reference-authoring flags.
It never reads an OCR prediction, error rate, confidence or success flag.
There is no threshold for obtaining a desired CER and no replacement of an
image after seeing its subset score.

The two tracks remain separate, with no pooled accuracy:

1. **KHOB digital exports:** every task-1 image in the existing 40-image
   comparison partition. This leaves one acquisition of each of the ten source
   documents. Previously used development documents remain excluded. Existing
   source transcripts and their limitations are retained unchanged.
2. **KH-FUNSD reference-screened candidates:** every supplied unique image with
   an empty recorded `uncertain_spans` list, no literal `[ILLEGIBLE]` marker,
   at least 50 Khmer letter/mark code points in its draft transcript, a shortest
   upright edge of at least 500 pixels and a longest edge of at least 1,000.
   The script counts Unicode categories L/M within U+1780–U+17D3, excluding
   Khmer digits and punctuation from this eligibility count. These thresholds
   are explicit convenience criteria, not validated readability measures.

All candidates then receive an assistant visual screen using the source image
and existing reference only. Record readable printed text, gross clipping,
obstruction and orientation. This screen cannot certify every character or
complete reference coverage. Rejections must record an input-quality reason;
uncertain candidates remain documented rather than being replaced to improve
an OCR score. No prediction is displayed to the screener.

Freeze the candidate manifest and final visual decisions before producing the
subset score report. Deterministic identities and source/reference SHA-256
values bind the selected units. Preserve all exclusion reasons and the earlier
complete benchmark results.

## Interpretation and scoring

KH-FUNSD references are the same author-designated machine-generated operational
ground truth used previously. `human_reviewed` and `reference_complete` remain
false. An empty uncertainty list is an authoring-model flag, not proof that a
reference is correct. Script membership does not certify language or coverage.
The filtered sample may omit entire categories and may repeat document
templates. Report its category and acquisition-folder composition explicitly.

Reuse unchanged frozen predictions and audited S/D/I counts. This diagnostic
does not rerun OCR, tune preprocessing, alter models, correct references,
deduplicate repeated model text, drop empty/capped/failed outputs, or clip error
rates. Report CER, whitespace-unit WER and segmentation-assisted WER with their
original definitions, denominators and failure accounting. Khmer word gold is
not supplied. Include only systems with complete coverage of the same selected
track; unmatched Qwen subsets must not appear as a full-track comparison.

The historical manuscripts, scene text, other acquisitions and low-quality
pages remain in their original robustness studies. A result on this focused
sample supports only that sample and cannot establish general OCR stability,
a sub-10% target, or an unbiased comparison across populations. Independently
corrected transcripts and new held-out documents are required for stronger
accuracy claims.
