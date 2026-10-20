# Accuracy artifacts

See [the evaluation guide](../../docs/ACCURACY.md) for interpretation.

The separate [KET-Tagger diagnostic](../../docs/TAGGER.md) records all 1,018
ALT test sentences with gold-boundary coverage, all-token/selective coarse
accuracy and joint coarse word/tag F1. `tagger/results.json` retains unknowns
and the failed authored compound-boundary target. The frozen
[tagger protocol](TAGGER_PROTOCOL.md) specifies the lossy NOVA mapping; these
scores do not validate fine Khmer particle tags. Existing OCR and report
artifacts are unchanged.

The [full-page study](../../docs/DOCUMENT_OCR.md) records five frozen OCR
implementations on 150 historical manuscript images, with separate results for
30 official CHURRO-DS test pages and 120 source-training stress pages. The
[small-model extension](../../docs/SMALL_VLM.md) adds two Qwen implementations
on the same 30 test images. These are historical handwriting comparisons,
separate from modern printed documents and three-OS installation checks.
The `document-ocr/` and `small-vlm/` directories retain source/model identities,
execution amendments, per-page counts and independent edit-count audits.
Private model-generated business-image transcripts are annotation drafts and
are excluded from benchmark scoring.

For current defaults, see [paired improvements](../../docs/IMPROVEMENTS.md).
See [the sub-10% experiment](../../docs/OCR_TARGET.md) and
[its reports](ocr-target/README.md) for the optional model comparison and a
swapped image/transcript pair discovered in development data. Historical
60-image and raw development aggregates include that mismatch; they remain
unchanged. The 40 comparison images exclude both affected IDs.
improvements/ contains paired baseline/development/reserved reports; the
IMPROVEMENT_PROTOCOL.md and IMPROVEMENT_SELECTION.md files record the policy
and development decision before reserved candidate predictions. Historical
leaf-tag POS measurements below remain available for comparison, but are not
the whole-word gold used by the latest evaluation.

- baseline/ contains untouched OCR, ALT POS, ALT sentence, and challenge
  results at runtime base commit 9e5e39738e630b3e17789ab20c46061c99ce1a07.
- results/ contains sentence/challenge reruns after the initials/phone fixes
  and the supplementary cross-corpus POS proxy. No model was trained.
- challenges.json is authored gold written before its predictions. It became
  development data when fixing the two bugs.
- Both protocol files were frozen before their respective predictions.

JSON names the base commit and hashes all runtime Python sources.
Baseline fingerprint:
67cc75025f64d968f41db88f0d5b668972ef71d98de10959d9d8ed308dbf08f2.
Adapted fingerprint:
b044bf6e91e361f0705cc983ddb2738ea0be63e899b3264388c0ee7fa034489e.
The base commit is HEAD before committing the evaluation and fixes; the source
fingerprint distinguishes the adapted working tree. Corpus/model and protocol
hashes identify inputs.

External gold text/images and full predictions remain excluded. This folder
contains derived aggregates, identifiers, metric counts and authored cases.
No live translation was performed.
