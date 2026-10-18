# Accuracy artifacts

See [the evaluation guide](../../docs/ACCURACY.md) for interpretation.

For current defaults, see [paired improvements](../../docs/IMPROVEMENTS.md).
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
